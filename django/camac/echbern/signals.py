import django.dispatch

instance_submitted = django.dispatch.Signal(providing_args=["instance", "group_pk"])

sb1_submitted = django.dispatch.Signal(providing_args=["instance", "group_pk"])
sb2_submitted = django.dispatch.Signal(providing_args=["instance", "group_pk"])
