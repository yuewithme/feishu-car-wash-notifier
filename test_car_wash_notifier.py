import unittest

try:
    from feishu_car_wash_notifier import car_wash_notifier
except ModuleNotFoundError:
    import car_wash_notifier


class CarWashNotifierTests(unittest.TestCase):
    def test_builds_card_from_configured_fields(self):
        payload = car_wash_notifier.sample_record()
        card = car_wash_notifier.build_car_wash_card(payload["fields"], payload["record_id"])

        self.assertEqual(card["config"]["wide_screen_mode"], True)
        self.assertEqual(card["header"]["title"]["content"], "洗车任务提醒")
        self.assertIn("沪A12345", card["elements"][0]["content"])
        self.assertIn("内外清洗", card["elements"][0]["content"])
        self.assertIn("sample_record_id", card["elements"][0]["content"])
        self.assertEqual(card["elements"][1]["actions"][0]["value"]["action"], "accept")
        self.assertEqual(card["elements"][1]["actions"][1]["value"]["action"], "done")
        self.assertEqual(card["elements"][1]["actions"][0]["text"]["content"], "接受任务")
        self.assertEqual(card["elements"][1]["actions"][1]["text"]["content"], "完成任务")

    def test_adds_upload_photo_button_after_accept(self):
        payload = car_wash_notifier.sample_record()
        card = car_wash_notifier.build_car_wash_card(payload["fields"], payload["record_id"], accepted=True)

        actions = card["elements"][1]["actions"]
        self.assertEqual(actions[2]["text"]["content"], "上传清洗照片")
        self.assertIn("record=sample_record_id", actions[2]["url"])

    def test_parses_card_action(self):
        event = {
            "header": {"event_type": "card.action.trigger", "event_id": "evt_1"},
            "event": {
                "action": {
                    "value": {
                        "action": "done",
                        "record_id": "rec_1",
                    }
                }
            },
        }

        self.assertEqual(
            car_wash_notifier.parse_card_action(event),
            {"action": "done", "record_id": "rec_1"},
        )

    def test_builds_accept_update_from_click_user(self):
        event = {"event": {"operator": {"open_id": "ou_cleaner"}}}
        self.assertEqual(car_wash_notifier.build_action_update("accept", event), {"清洗人员": [{"id": "ou_cleaner"}]})

    def test_builds_done_update_with_completion_time(self):
        update = car_wash_notifier.build_action_update("done")
        self.assertIn("清洗完成时间", update)
        self.assertRegex(update["清洗完成时间"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_ignores_unknown_action(self):
        self.assertEqual(car_wash_notifier.build_action_update("unknown"), {})

    def test_parses_new_record_event(self):
        event = {
            "header": {"event_type": "bitable.record.created_v1"},
            "event": {
                "base_token": "LdiKbOgd7a5FSvsgNO5c0DNunTa",
                "table_id": "tblaTXQqJNNAzMSS",
                "record_id": "rec_1",
            },
        }

        self.assertEqual(car_wash_notifier.parse_new_record_event(event), "rec_1")


if __name__ == "__main__":
    unittest.main()
