from django.test import TestCase

from core.models import User
from issues.models import Issue
from projects.models import Project
from risks.models import Risk
from tasks.models import Task

from .agent import ProjectIntelligenceAgent
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
        )

        self.assertEqual(result.title, 'Project Health Assessment')
        self.assertTrue(result.findings)
        self.assertTrue(result.recommendations)
        self.assertIn('project_health', [item['tool'] for item in result.tool_outputs])
