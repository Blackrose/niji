from django.test import TestCase
from django.contrib.auth.models import User
from .models import Topic, Node, Post, Notification


class TopicModelTest(TestCase):

    def setUp(self):
        self.n1 = Node.objects.create(
            title='TestNodeOne',
            description='The first test node'
        )
        self.u1 = User.objects.create_user(
            username='test1', email='1@q.com', password='111'
        )
        self.u2 = User.objects.create_user(
            username='test2', email='2@q.com', password='222'
        )
        self.t1 = Topic.objects.create(
            title='Test Topic 1',
            user=self.u1,
            content_raw='This is test topic __1__',
            node=self.n1,
        )
        self.t2 = Topic.objects.create(
            title='Test Topic 2',
            user=self.u1,
            content_raw='This is test topic __2__',
            node=self.n1,
        )

    def test_hidden_topic(self):
        self.assertEqual(Topic.objects.visible().count(), 2)
        self.t1.hidden = True
        self.t1.save()
        self.assertEqual(Topic.objects.visible().count(), 1)

    def test_topic_order(self):
        self.assertEqual(Topic.objects.visible().first(), self.t2)
        self.t1.order = 9
        self.t1.save()
        self.assertEqual(Topic.objects.visible().first(), self.t1)

    def test_topic_content_hash(self):
        original_hash = self.t1.raw_content_hash
        self.t1.content_raw = 'fdsfds'
        self.t1.save()
        self.assertNotEqual(original_hash, self.t1.raw_content_hash)
        self.t1.content_raw = 'This is test topic __1__'
        self.t1.save()
        self.assertEqual(original_hash, self.t1.raw_content_hash)

    def test_content_render(self):
        self.assertIn('<strong>1</strong>', self.t1.content_rendered)
        self.t1.content_raw = 'This is the __first__ topic'
        self.t1.save()
        self.assertIn('<strong>first</strong>', self.t1.content_rendered)

    def test_last_replied(self):
        p = Post()
        p.topic = self.t1
        p.content_raw = 'reply to post __1__'
        p.user = self.u1
        p.save()
        self.assertEqual(self.t1.last_replied, p.pub_date)
        p2 = Post()
        p2.topic = self.t1
        p2.content_raw = '2nd reply to post __1__'
        p2.user = self.u1
        p2.save()
        self.assertEqual(self.t1.last_replied, p2.pub_date)
        p2.delete()
        self.assertEqual(self.t1.last_replied, p.pub_date)
        p.delete()
        self.assertEqual(self.t1.last_replied, self.t1.pub_date)

    def test_reply_count(self):
        p = Post()
        p.topic = self.t1
        p.content_raw = '2nd reply to post __1__'
        p.user = self.u1
        p.save()
        self.assertEqual(self.t1.reply_count, 1)
        p.pk += 1
        p.save()
        self.assertEqual(self.t1.reply_count, 2)
        p.hidden = True
        p.save()
        self.assertEqual(self.t1.reply_count, 1)
        p.hidden = False
        p.save()
        self.assertEqual(self.t1.reply_count, 2)
        p.delete()
        self.assertEqual(self.t1.reply_count, 1)

    def test_other_user_mention(self):
        t = Topic.objects.create(
            title='topic mention test',
            user=self.u1,
            content_raw='test mention @test2',
            node=self.n1,
        )
        self.assertEqual(self.u2.received_notifications.count(), 1)
        notification = Notification.objects.get(pk=1)
        self.assertEqual(notification.topic_id, t.pk)
        self.assertEqual(notification.sender_id, self.u1.pk)
        self.assertEqual(notification.to_id, self.u2.pk)

    def test_self_mention(self):
        Topic.objects.create(
            title='topic mention test',
            user=self.u1,
            content_raw='test mention myself @test1',
            node=self.n1,
        )
        self.assertEqual(self.u1.received_notifications.count(), 0)


class PostModelTest(TestCase):

    def setUp(self):
        self.n1 = Node.objects.create(
            title='TestNodeOne',
            description='The first test node'
        )
        self.u1 = User.objects.create_user(
            username='test1', email='1@q.com', password='111'
        )
        self.u2 = User.objects.create_user(
            username='test2', email='2@q.com', password='222'
        )
        self.t1 = Topic.objects.create(
            title='Test Topic 1',
            user=self.u1,
            content_raw='This is test topic __1__',
            node=self.n1,
        )
        self.p1 = Post.objects.create(
            topic=self.t1,
            content_raw='reply to post __1__',
            user=self.u1,
        )
        self.p2 = Post.objects.create(
            topic=self.t1,
            content_raw='reply to post __2__',
            user=self.u1,
        )

    def test_content_render(self):
        self.assertIn('<strong>1</strong>', self.p1.content_rendered)
        self.p1.content_raw = 'This is the __first__ reply'
        self.p1.save()
        self.assertIn('<strong>first</strong>', self.p1.content_rendered)

    def test_hidden(self):
        self.assertEqual(self.t1.replies.visible().count(), 2)
        self.p1.hidden = True
        self.p1.save()
        self.assertEqual(self.t1.replies.visible().count(), 1)

    def test_other_user_mention(self):
        p = Post.objects.create(
            user=self.u1,
            content_raw='test mention @test2',
            topic=self.t1,
        )
        self.assertEqual(self.u2.received_notifications.count(), 1)
        notification = Notification.objects.get(pk=1)
        self.assertEqual(notification.post_id, p.pk)
        self.assertEqual(notification.sender_id, self.u1.pk)
        self.assertEqual(notification.to_id, self.u2.pk)

    def test_self_mention(self):
        Post.objects.create(
            user=self.u1,
            content_raw='test to mention myself @test1',
            topic=self.t1,
        )
        self.assertEqual(self.u1.received_notifications.count(), 0)