import os
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from core.models import Role, User
from issues.models import Issue
from projects.models import Project
from risks.models import Risk
from tasks.models import Task

from .agent import ProjectIntelligenceAgent
from .llm import generate_project_report, normalize_llm_report
from .llm_providers import LLMFactory
from .planner import Planner
from .registry import default_tool_registry
from .state import AgentState
from .tools import project_health


class ProjectIntelligenceAgentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='pm@example.com',
            password='test-pass',
            is_staff=True,
        )
        self.project = Project.objects.create(
            name='Nexus Delivery',
            code='ND',
            project_type='INTERNAL',
            status='ACTIVE',
            priority='HIGH',
            owner=self.user,
            created_by=self.user,
        )
        self.pm_role = Role.objects.create(name='Project Manager')
        self.non_admin_user = User.objects.create_user(
            email='pm-user@example.com',
            password='test-pass',
        )
        self.non_admin_user.roles.add(self.pm_role)
        Task.objects.create(
            task_id='ND-1',
            project=self.project,
            title='Blocked integration task',
            status='BLOCKED',
            priority='HIGH',
            story_points=5,
            assignee=self.user,
            created_by=self.user,
        )
        Issue.objects.create(
            project=self.project,
            title='Major deployment issue',
            issue_type='BUG',
            severity='MAJOR',
            status='OPEN',
            created_by=self.user,
        )
        Risk.objects.create(
            risk_id='RISK-1',
            project=self.project,
            title='Delivery capacity risk',
            description='Team capacity may not cover planned scope.',
            probability=3,
            impact=4,
            owner=self.user,
            created_by=self.user,
        )

    def test_project_health_tool_returns_verified_metrics(self):
        data = project_health(self.project.pk, self.user)

        self.assertEqual(data['tool'], 'project_health')
        self.assertEqual(data['project']['code'], 'ND')
        self.assertEqual(data['health']['signals']['blocked_tasks'], 1)
        self.assertEqual(data['health']['signals']['severe_open_issues'], 1)
        self.assertEqual(data['health']['signals']['high_or_critical_risks'], 1)

    def test_agent_generates_project_health_report(self):
        result = ProjectIntelligenceAgent(self.user).analyze(
            'prepare a health report',
            'project_health',
            project_id=self.project.pk,
            use_llm=False,
        )

        self.assertEqual(result.title, 'Project Health Assessment')
        self.assertTrue(result.findings)
        self.assertTrue(result.recommendations)
        self.assertIn('project_health', [item['tool'] for item in result.tool_outputs])

    def test_agent_can_use_llm_report_writer_after_tools_run(self):
        llm_payload = {
            'title': 'AI Project Health Report',
            'executive_summary': 'The project requires management attention.',
            'narrative': 'The verified tool outputs show blocked work, a major issue, and a critical risk.',
            'findings': ['Blocked work is affecting delivery.'],
            'recommendations': ['Assign a recovery owner for the blocked task.'],
            'sections': [{'heading': 'Delivery Outlook', 'items': ['Health score is pressure-sensitive.']}],
        }

        with patch('ai_assistant.response_generator.is_llm_configured', return_value=True), \
             patch('ai_assistant.response_generator.generate_project_report', return_value=llm_payload) as mock_writer:
            result = ProjectIntelligenceAgent(self.user).analyze(
                'prepare an executive report',
                'project_health',
                project_id=self.project.pk,
            )

        self.assertEqual(result.generation_mode, 'OpenAI Enhanced')
        self.assertEqual(result.title, 'AI Project Health Report')
        self.assertTrue(result.narrative)
        self.assertIn('project_health', [item['tool'] for item in result.tool_outputs])
        self.assertTrue(mock_writer.called)

    def test_llm_report_normalization_falls_back_for_missing_fields(self):
        baseline = ProjectIntelligenceAgent(self.user).analyze(
            'prepare a health report',
            'project_health',
            project_id=self.project.pk,
            use_llm=False,
        )

        normalized = normalize_llm_report({'title': 'Partial Report'}, baseline)

        self.assertEqual(normalized['title'], 'Partial Report')
        self.assertEqual(normalized['executive_summary'], baseline.executive_summary)
        self.assertEqual(normalized['findings'], baseline.findings)

    def test_planner_returns_structured_plan(self):
        state = AgentState(
            question='prepare a health report',
            report_type='project_health',
            project_id=self.project.pk,
        )

        plan = Planner(self.user).plan(state)

        self.assertEqual(plan.objective, 'Project Health Assessment')
        self.assertEqual(plan.status, 'ready')
        self.assertEqual(plan.required_tools[0].name, 'project_health')
        self.assertEqual(plan.required_tools[0].parameters['project_id'], self.project.pk)
        self.assertEqual(state.current_plan, plan)

    def test_tool_registry_executes_tools_with_structured_parameters(self):
        output = default_tool_registry.execute(
            'project_health',
            {'project_id': self.project.pk},
            {'user': self.user},
        )

        self.assertEqual(output['tool'], 'project_health')
        self.assertEqual(output['project']['code'], 'ND')
        self.assertEqual(default_tool_registry.get('project_health').name, 'project_health')

    def test_llm_factory_defaults_to_openai_provider(self):
        with patch('ai_assistant.llm_config.load_local_env'), \
             patch.dict(os.environ, {
                 'LLM_PROVIDER': 'OPENAI',
                 'OPENAI_API_KEY': 'test-key',
                 'OPENAI_MODEL': 'test-model',
             }, clear=True):
            provider = LLMFactory.create()

        self.assertEqual(provider.provider_name, 'OPENAI')
        self.assertTrue(provider.is_configured())
        self.assertEqual(provider.config.model, 'test-model')

    def test_llm_factory_returns_placeholder_provider(self):
        with patch('ai_assistant.llm_config.load_local_env'), \
             patch.dict(os.environ, {
                 'LLM_PROVIDER': 'GEMINI',
                 'GEMINI_API_KEY': 'test-key',
                 'GEMINI_MODEL': 'gemini-test',
             }, clear=True):
            provider = LLMFactory.create()

        self.assertEqual(provider.provider_name, 'GEMINI')
        self.assertTrue(provider.is_configured())
        self.assertEqual(provider.config.model, 'gemini-test')

    def test_llm_factory_supports_grok_provider_with_current_env_names(self):
        with patch('ai_assistant.llm_config.load_local_env'), \
             patch.dict(os.environ, {
                 'LLM_PROVIDER': 'GROK',
                 'GROQ_API_KEY': 'xai-test-key',
                 'GROQ_MODEL': 'grok-code-fast-1',
             }, clear=True):
            provider = LLMFactory.create()

        self.assertEqual(provider.provider_name, 'GROK')
        self.assertTrue(provider.is_configured())
        self.assertEqual(provider.config.api_key, 'xai-test-key')
        self.assertEqual(provider.config.model, 'grok-code-fast-1')
        self.assertEqual(provider.config.endpoint, 'https://api.x.ai/v1')

    def test_llm_factory_supports_xai_alias(self):
        with patch('ai_assistant.llm_config.load_local_env'), \
             patch.dict(os.environ, {
                 'LLM_PROVIDER': 'XAI',
                 'XAI_API_KEY': 'xai-test-key',
                 'XAI_MODEL': 'grok-test',
                 'XAI_BASE_URL': 'https://example.test/v1',
             }, clear=True):
            provider = LLMFactory.create()

        self.assertEqual(provider.provider_name, 'GROK')
        self.assertTrue(provider.is_configured())
        self.assertEqual(provider.config.model, 'grok-test')
        self.assertEqual(provider.config.endpoint, 'https://example.test/v1')

    def test_generate_project_report_uses_provider_facade(self):
        baseline = ProjectIntelligenceAgent(self.user).analyze(
            'prepare a health report',
            'project_health',
            project_id=self.project.pk,
            use_llm=False,
        )

        class FakeProvider:
            def structured_output(self, system_prompt, user_payload, schema, schema_name):
                return {
                    'title': 'Provider Report',
                    'executive_summary': 'Provider-generated summary.',
                    'narrative': 'Provider-generated narrative.',
                    'findings': ['Provider finding.'],
                    'recommendations': ['Provider recommendation.'],
                    'sections': [{'heading': 'Provider Section', 'items': ['Provider item.']}],
                }

        with patch('ai_assistant.llm.LLMFactory.create', return_value=FakeProvider()):
            report = generate_project_report(
                prompt='prepare report',
                report_type='project_health',
                tool_outputs=[],
                deterministic_report=baseline,
            )

        self.assertEqual(report['title'], 'Provider Report')
        self.assertEqual(report['findings'], ['Provider finding.'])

    def test_system_admin_can_access_pia_home(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('pia_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Project Intelligence Agent')

    def test_non_system_admin_cannot_access_pia_home(self):
        self.client.force_login(self.non_admin_user)

        response = self.client.get(reverse('pia_home'))

        self.assertEqual(response.status_code, 403)

    def test_non_system_admin_cannot_access_pia_api(self):
        self.client.force_login(self.non_admin_user)

        response = self.client.post(
            reverse('pia_analyze_api'),
            data='{"prompt": "portfolio summary", "report_type": "portfolio"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_system_admin_can_access_pia_api(self):
        self.client.force_login(self.user)

        with patch('ai_assistant.response_generator.is_llm_configured', return_value=False):
            response = self.client.post(
                reverse('pia_analyze_api'),
                data='{"prompt": "portfolio summary", "report_type": "portfolio"}',
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], 'Portfolio Summary')

    def test_sidebar_hides_pia_for_non_system_admin(self):
        self.client.force_login(self.non_admin_user)

        response = self.client.get(reverse('project_list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'PIA')

    def test_sidebar_shows_pia_for_system_admin(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('project_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PIA')
