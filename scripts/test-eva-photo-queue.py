import importlib.util
import unittest
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock


spec = importlib.util.spec_from_file_location(
    "eva_photo_queue", Path(__file__).with_name("eva-photo-queue.py")
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class PhotoQueueTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 19, 10, tzinfo=timezone.utc)
        self.contacts = {
            "one": {"id": "one", "phone": "+7 999 000 00 01", "props": {"partnersegment": "design"}},
            "alias": {"id": "alias", "phone": "89990000001"},
            "two": {"id": "two", "phone": "79990000002", "props": {"partnersegment": "design"}},
        }
        self.aliases = defaultdict(set)
        for contact in self.contacts.values():
            self.aliases[guard.phone_key(contact)].add(contact["id"])
        self.task = {
            "id": "task", "userId": "victoria", "channels": ["tg"], "enabled": True,
            "autoSyncContacts": False, "scheduleId": "schedule",
        }
        self.lane = {
            "task": "task", "kind": "telegram", "channel": "tg",
            "recipients": [
                {"contactId": uid, "phone": guard.phone_key(self.contacts[uid]),
                 "segment": "design", "prompt": f"caption for {uid}"}
                for uid in ("one", "two")
            ],
        }
        self.state = {"telegram": {}}
        self.commit = Mock()
        self.eva = Mock()
        self.eva.KALININGRAD = timezone.utc
        self.eva.working.return_value = True
        self.eva.timestamp.return_value = None
        self.eva.eligible.return_value = True
        self.eva.task_rows.return_value = []
        self.eva.record.side_effect = self.record
        self.eva.records.side_effect = self.history
        self.eva.api.return_value = {"items": [{"contactId": "two"}]}

    def record(self, resource, uid):
        if resource == "contacts":
            return self.contacts.get(uid)
        return {
            "channels": {"userId": "victoria", "type": "telegram",
                         "status": "online", "enabledMode": "enabled"},
            "documents": {"userId": "victoria", "status": "complete",
                          "type": "image", "accessMode": "sendToChat"},
            "schedules": {"isWorking": True},
            "tasks": self.task,
            "taskcontacts": None,
        }[resource]

    @staticmethod
    def history(resource, **query):
        if resource == "conversations":
            uid = query["contactId"]
            return [{"id": uid, "contactId": uid}] if uid in ("alias", "two") else []
        if query["conversationId"] == "alias":
            return [{"conversationId": "alias", "senderType": "user", "text": "Уже общались"}]
        return []  # An empty chat left by a failed attempt.

    def dispatch(self):
        return guard.dispatch_lane(
            self.eva, self.lane, {"worker": "victoria", "document": "photo"}, self.state,
            self.commit, {"task": self.task}, self.contacts, self.aliases, self.now,
        )

    def test_skips_existing_dialogue_on_alias_and_releases_only_one(self):
        self.assertEqual(self.dispatch(), "released")
        self.assertEqual(self.state["telegram"]["one"]["outcome"], "existing_dialogue")
        sent = list(self.eva.api.call_args.args[2]["data"].values())
        self.assertEqual([(item["contactId"], item["prompt"]) for item in sent], [("two", "caption for two")])

    def test_history_error_leaves_queue_empty(self):
        self.eva.records.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.dispatch()
        self.eva.api.assert_not_called()
        self.assertEqual(self.state["telegram"], {})

    def test_pending_recipient_who_replied_is_removed(self):
        row = {"id": "row", "contactId": "one", "status": "queue"}
        self.eva.task_rows.return_value = [row]
        self.state["telegram"]["one"] = {"outcome": "queued"}
        self.assertEqual(self.dispatch(), "existing_dialogue")
        self.eva.cancel.assert_called_once_with([row])
        self.eva.api.assert_not_called()

    def test_uncertain_post_is_not_retried(self):
        self.eva.api.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.dispatch()
        self.assertEqual(self.dispatch(), "waiting_for_uncertain_write")
        self.eva.api.assert_called_once()


if __name__ == "__main__":
    unittest.main()
