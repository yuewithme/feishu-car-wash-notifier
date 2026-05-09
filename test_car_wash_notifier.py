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
        self.assertIn("车辆返回场站时间", card["elements"][0]["content"])
        self.assertIn("2026-05-08 16:30:00", card["elements"][0]["content"])
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
        self.assertNotIn("value", actions[2])

    def test_adds_upload_button_to_existing_card_without_refetch(self):
        card = car_wash_notifier.build_car_wash_card(car_wash_notifier.sample_record()["fields"], "rec_1")
        event = {"event": {"action": {"card": card}}}

        updated = car_wash_notifier.add_upload_button_to_card_event(event, "rec_1")

        actions = updated["elements"][1]["actions"]
        self.assertEqual(actions[2]["text"]["content"], "上传清洗照片")
        self.assertIn("record=rec_1", actions[2]["url"])
        self.assertNotIn("value", actions[2])

    def test_adds_upload_button_to_cached_card_without_losing_fields(self):
        card = car_wash_notifier.build_car_wash_card(car_wash_notifier.sample_record()["fields"], "rec_1")

        updated = car_wash_notifier.add_upload_button_to_card(card, "rec_1")

        content = updated["elements"][0]["content"]
        self.assertIn("沪A12345", content)
        self.assertIn("内外清洗", content)
        self.assertIn("2026-05-08 16:30:00", content)
        self.assertIn("record=rec_1", updated["elements"][1]["actions"][2]["url"])
        self.assertNotIn("value", updated["elements"][1]["actions"][2])

    def test_marks_done_button_cleaned_and_disabled(self):
        card = car_wash_notifier.build_car_wash_card(car_wash_notifier.sample_record()["fields"], "rec_1")

        updated = car_wash_notifier.mark_done_button_cleaned(card)

        done_button = updated["elements"][1]["actions"][1]
        self.assertEqual(done_button["text"]["content"], "已清洗")
        self.assertEqual(done_button["disabled"], True)
        self.assertIn("沪A12345", updated["elements"][0]["content"])

    def test_marks_group_card_accepted_and_disabled(self):
        card = car_wash_notifier.build_car_wash_card(car_wash_notifier.sample_record()["fields"], "rec_1")

        updated = car_wash_notifier.mark_group_card_accepted(card, "ou_cleaner")

        self.assertIn("<at id=ou_cleaner></at>已接清洗任务", updated["elements"][0]["content"])
        for action in updated["elements"][1]["actions"]:
            self.assertEqual(action["disabled"], True)

    def test_builds_private_work_card_after_accept(self):
        card = car_wash_notifier.build_private_work_card(car_wash_notifier.sample_record()["fields"], "rec_1")

        actions = card["elements"][1]["actions"]
        self.assertEqual(actions[0]["value"]["action"], "done")
        self.assertEqual(len(actions), 1)
        self.assertIn("上传清洗照片", card["elements"][0]["content"])
        self.assertIn("record=rec_1", card["elements"][0]["content"])
        self.assertNotIn("接受任务", str(actions))

    def test_private_work_card_has_no_url_button(self):
        card = car_wash_notifier.build_private_work_card(car_wash_notifier.sample_record()["fields"], "rec_1")

        actions = card["elements"][1]["actions"]
        self.assertEqual(len(actions), 1)
        self.assertNotIn("url", str(actions))

    def test_parse_sent_message_id_from_cli_output(self):
        output = '{"data":{"message_id":"om_123"}}'

        self.assertEqual(car_wash_notifier.parse_sent_message_id(output), "om_123")

    def test_sanitizes_idempotency_key_for_lark(self):
        key = car_wash_notifier.build_idempotency_key("rec_1-private-ou_abc")

        self.assertEqual(key, "car-wash-card-rec-1-private-ou-abc")
        self.assertNotIn("_", key)

    def test_duplicate_field_error_is_treated_as_existing_field(self):
        stderr = 'validation_error Use a unique field name. Existing field: fldwoFyAra("任务状态"). Requested field name: "任务状态".'

        self.assertTrue(car_wash_notifier.is_duplicate_field_error(stderr, "任务状态"))

    def test_should_not_notify_record_with_group_message_id(self):
        self.assertFalse(
            car_wash_notifier.should_notify_record(
                {
                    "车牌号": [{"id": "rec_vehicle"}],
                    "清洗需求": ["需要小清洗"],
                    "群消息ID": "om_sent",
                }
            )
        )

    def test_done_requires_photo_before_update(self):
        update = car_wash_notifier.build_action_update(
            "done",
            record_fields={"清洗照片": None},
        )

        self.assertEqual(update, {})

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
        self.assertEqual(
            car_wash_notifier.build_action_update("accept", event),
            {"清洗人员": [{"id": "ou_cleaner"}], "任务状态": "已接单"},
        )

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

    def test_parses_drive_bitable_record_added_event(self):
        event = {
            "header": {"event_type": "drive.file.bitable_record_changed_v1"},
            "event": {
                "file_token": "LdiKbOgd7a5FSvsgNO5c0DNunTa",
                "table_id": "tblaTXQqJNNAzMSS",
                "action_list": [
                    {"action": "record_edited", "record_id": "rec_ignore"},
                    {"action": "record_added", "record_id": "rec_added"},
                ],
            },
        }

        self.assertEqual(car_wash_notifier.parse_new_record_event(event), "rec_added")

    def test_detects_link_value_that_needs_display_resolution(self):
        self.assertTrue(car_wash_notifier.needs_link_display_resolution([{"id": "rec_vehicle"}]))
        self.assertFalse(car_wash_notifier.needs_link_display_resolution([{"id": "rec_vehicle", "text": "沪A12345"}]))

    def test_should_notify_record_requires_plate_and_need(self):
        self.assertTrue(
            car_wash_notifier.should_notify_record(
                {"车牌号": [{"id": "rec_vehicle"}], "清洗需求": ["需要小清洗"]}
            )
        )
        self.assertFalse(car_wash_notifier.should_notify_record({"车牌号": [{"id": "rec_vehicle"}]}))


if __name__ == "__main__":
    unittest.main()
