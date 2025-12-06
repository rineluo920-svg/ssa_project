from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Group(models.Model):
    name = models.CharField(max_length=100)
    admin = models.ForeignKey(User, related_name='admin_groups', on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='group_memberships', blank=True)
    invited_users = models.ManyToManyField(User, related_name='pending_invitations', blank=True)
    def __str__(self):
        return self.name

class GroupJoinRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='join_requests')
    is_approved = models.BooleanField(default=False)
    votes = models.ManyToManyField(User, related_name='votes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # User who posted the comment
    group = models.ForeignKey(Group, related_name='comments', on_delete=models.CASCADE)  # Group associated with the comment
    content = models.TextField()  # The comment content
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the comment was posted
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for the latest update

    def __str__(self):
        return f"{self.user.username}: {self.content[:20]}..."  # Show only first 20 chars for preview'

class Event(models.Model):
    class Status(models.TextChoices):
        PENDING  = "Pending",  "Pending"
        ACTIVE   = "Active",   "Active"
        ARCHIVED = "Archived", "Archived" 
    name = models.CharField(max_length=100)
    date = models.DateField()
    total_spend = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    group = models.ForeignKey(Group, related_name='events', on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='event_memberships', blank=True)  
    def calculate_share(self):
        members_count = self.group.members.count()
        return 0 if members_count == 0 else self.total_spend / members_count
    def check_status(self, save=True):
        if self.status == self.Status.ARCHIVED:
            return self.status
        share = self.calculate_share()
        for member in self.group.members.all():
            if member.profile.max_spend < share:
                self.status = self.Status.PENDING
                if save:
                    self.save(update_fields=["status"])
                return self.status
        self.status = self.Status.ACTIVE
        if save:
            self.save(update_fields=["status"])
        return self.status
    def archive(self, save=True):
        self.status = self.Status.ARCHIVED
        self.archived_at = timezone.now()
        if save:
            self.save(update_fields=["status", "archived_at"])
