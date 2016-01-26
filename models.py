from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import python_2_unicode_compatible
import xxhash
import mistune
import re


MENTION_REGEX = re.compile(r'@(\S+)\s', re.M)


def render_content(content_raw):
    """
    :param content_raw: Raw content
    :return: (rendered_content, mentioned_user_list)
    """
    content_rendered = mistune.markdown(content_raw)
    mentioned = set(re.findall(MENTION_REGEX, content_raw))
    mentioned_users = User.objects.filter(username__in=mentioned)
    return content_rendered, mentioned_users


class TopicQueryset(models.QuerySet):

    def visible(self):
        return self.filter(hidden=False)


@python_2_unicode_compatible
class Topic(models.Model):
    user = models.ForeignKey(User, related_name='topics')
    title = models.CharField(max_length=120)
    content_raw = models.TextField()
    content_rendered = models.TextField(default='', blank=True)
    view_count = models.IntegerField(default=0)
    reply_count = models.IntegerField(default=0)
    node = models.ForeignKey('Node', related_name='topics')
    pub_date = models.DateTimeField(auto_now_add=True, db_index=True)
    last_replied = models.DateTimeField(auto_now_add=True, db_index=True)
    order = models.IntegerField(default=10)
    hidden = models.BooleanField(default=False)
    objects = TopicQueryset.as_manager()

    raw_content_hash = None

    def __init__(self, *args, **kwargs):
        super(Topic, self).__init__(*args, **kwargs)
        self.raw_content_hash = xxhash.xxh64(self.content_raw).hexdigest()

    def get_reply_count(self):
        return self.replies.visible().count()

    def get_last_replied(self):
        last_visible_reply = self.replies.visible().order_by('-pub_date').first()
        if last_visible_reply:
            return last_visible_reply.pub_date
        return self.pub_date

    def save(self, *args, **kwargs):
        new_hash = xxhash.xxh64(self.content_raw).hexdigest()
        if new_hash != self.raw_content_hash or (not self.pk):
            # To (re-)render the content if content changed or topic is newly created
            self.content_rendered, mentioned_users = render_content(self.content_raw)
        super(Topic, self).save(*args, **kwargs)
        self.raw_content_hash = new_hash

    class Meta:
        ordering = ['order', '-pub_date']

    def __str__(self):
        return self.title


class PostQueryset(models.QuerySet):

    use_for_related_fields = True

    def visible(self):
        return self.filter(hidden=False)


@python_2_unicode_compatible
class Post(models.Model):
    topic = models.ForeignKey('Topic', related_name='replies')
    user = models.ForeignKey(User, related_name='posts')
    content_raw = models.TextField()
    content_rendered = models.TextField(default='')
    pub_date = models.DateTimeField(auto_now_add=True)
    hidden = models.BooleanField(default=False)
    objects = PostQueryset.as_manager()

    raw_content_hash = None

    def __init__(self, *args, **kwargs):
        super(Post, self).__init__(*args, **kwargs)
        self.raw_content_hash = xxhash.xxh64(self.content_raw).hexdigest()

    def __str__(self):
        return 'Reply to %s' % self.topic.title

    def save(self, *args, **kwargs):
        new_hash = xxhash.xxh64(self.content_raw).hexdigest()
        if new_hash != self.raw_content_hash or (not self.pk):
            self.content_rendered, mentioned_users = render_content(self.content_raw)
        super(Post, self).save(*args, **kwargs)
        t = self.topic
        t.reply_count = t.get_reply_count()
        t.last_replied = t.get_last_replied()
        t.save(update_fields=['last_replied', 'reply_count'])

    def delete(self, *args, **kwargs):
        super(Post, self).delete(*args, **kwargs)
        t = self.topic
        t.reply_count = t.get_reply_count()
        t.last_replied = t.get_last_replied()
        t.save(update_fields=['last_replied', 'reply_count'])


@python_2_unicode_compatible
class Notification(models.Model):
    sender = models.ForeignKey(User, related_name='sent_notifications')
    to = models.ForeignKey(User, related_name='received_notifications')
    topic = models.ForeignKey('Topic')
    post = models.ForeignKey('Post', null=True)
    read = models.BooleanField(default=False)
    pub_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'Notification from %s to %s' % (self.sender.username, self.to.username)


@python_2_unicode_compatible
class Appendix(models.Model):
    topic = models.ForeignKey('Topic')
    pub_date = models.DateTimeField(auto_now_add=True)
    content_raw = models.TextField()
    content_rendered = models.TextField(default='', blank=True)

    def __str__(self):
        return 'Appendix to %s' % self.topic.title


@python_2_unicode_compatible
class Node(models.Model):
    title = models.CharField(max_length=30)
    description = models.TextField(default='', blank=True)

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class NodeGroup(models.Model):
    title = models.CharField(max_length=30)
    node = models.ManyToManyField('Node')

    def __str__(self):
        return self.title