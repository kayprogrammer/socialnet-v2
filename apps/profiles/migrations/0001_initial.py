# Generated by Django 4.2.3 on 2023-10-10 20:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.functions.comparison
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("feed", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ntype",
                    models.CharField(
                        choices=[
                            ("REACTION", "REACTION"),
                            ("COMMENT", "COMMENT"),
                            ("REPLY", "REPLY"),
                            ("ADMIN", "ADMIN"),
                        ],
                        max_length=100,
                        verbose_name="Type",
                    ),
                ),
                ("text", models.CharField(max_length=100, null=True)),
                (
                    "comment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="feed.comment",
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="feed.post",
                    ),
                ),
                (
                    "read_by",
                    models.ManyToManyField(
                        blank=True,
                        related_name="notifications_read",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "receivers",
                    models.ManyToManyField(
                        related_name="notifications", to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "reply",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="feed.reply",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications_from",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Friend",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "PENDING"), ("ACCEPTED", "ACCEPTED")],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                (
                    "requestee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="requestee_friends",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="requester_friends",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("comment", None), ("post__isnull", False), ("reply", None)
                    ),
                    models.Q(
                        ("comment__isnull", False), ("post", None), ("reply", None)
                    ),
                    models.Q(
                        ("comment", None), ("post", None), ("reply__isnull", False)
                    ),
                    models.Q(
                        ("comment", None),
                        ("ntype", "ADMIN"),
                        ("post", None),
                        ("reply", None),
                    ),
                    _connector="OR",
                ),
                name="selected_object_constraints",
                violation_error_message="\n                        * Cannot have cannot have post, comment, reply or any two of the three simultaneously. <br/>\n                        &ensp;&ensp;&nbsp;&nbsp;&nbsp;&nbsp;* If the three are None, then it must be of type 'ADMIN'\n                    ",
            ),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("ntype", "ADMIN"), ("sender", None), ("text__isnull", False)
                    ),
                    models.Q(
                        models.Q(("ntype", "ADMIN"), _negated=True),
                        ("sender__isnull", False),
                        ("text", None),
                    ),
                    _connector="OR",
                ),
                name="sender_text_type_constraints",
                violation_error_message="If No Sender, type must be ADMIN and text must not be empty and vice versa.",
            ),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(
                            ("ntype", "ADMIN"), ("ntype", "REACTION"), _connector="OR"
                        ),
                        ("post__isnull", False),
                    ),
                    models.Q(
                        models.Q(
                            ("ntype", "COMMENT"), ("ntype", "REACTION"), _connector="OR"
                        ),
                        ("comment__isnull", False),
                    ),
                    models.Q(
                        models.Q(
                            ("ntype", "REPLY"), ("ntype", "REACTION"), _connector="OR"
                        ),
                        ("reply__isnull", False),
                    ),
                    models.Q(
                        ("comment", None),
                        ("ntype", "ADMIN"),
                        ("post", None),
                        ("reply", None),
                    ),
                    _connector="OR",
                ),
                name="post_comment_reply_type_constraints",
                violation_error_message="\n                        * If Post, type must be ADMIN or REACTION. <br/>\n                        &ensp;&ensp;&nbsp;&nbsp;&nbsp;&nbsp;* If Comment, type must be COMMENT or REACTION. <br/>\n                        &ensp;&ensp;&nbsp;&nbsp;&nbsp;&nbsp;* If Reply, type must be REPLY or REACTION. <br/>\n                    ",
            ),
        ),
        migrations.AddConstraint(
            model_name="friend",
            constraint=models.UniqueConstraint(
                django.db.models.functions.comparison.Least("requester", "requestee"),
                django.db.models.functions.comparison.Greatest(
                    "requester", "requestee"
                ),
                name="bidirectional_unique_user_combination",
                violation_error_message="Friend with similar users already exists",
            ),
        ),
        migrations.AddConstraint(
            model_name="friend",
            constraint=models.CheckConstraint(
                check=models.Q(("requester", models.F("requestee")), _negated=True),
                name="different_users",
                violation_error_message="Requester and Requestee cannot be the same",
            ),
        ),
    ]
