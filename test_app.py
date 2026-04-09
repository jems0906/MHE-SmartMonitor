import unittest

from app import app


class SmartMonitorApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = app.test_client()

    def test_health_endpoint(self) -> None:
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'ok')

    def test_status_payload_contains_core_fields(self) -> None:
        response = self.client.get('/api/status')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        for key in [
            'throughput_rate',
            'motor_status',
            'health_status',
            'plc_mode',
            'line_state',
            'alarm_code',
            'alarm_status',
            'sensors',
        ]:
            self.assertIn(key, data)

    def test_report_endpoint_returns_summary(self) -> None:
        response = self.client.get('/api/report')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        for key in ['samples', 'avg_throughput', 'availability_pct', 'critical_events']:
            self.assertIn(key, data)

    def test_control_endpoint_rejects_invalid_action(self) -> None:
        response = self.client.post('/api/control', json={'action': 'bad-action'})
        self.assertEqual(response.status_code, 400)

    def test_acknowledge_alarm_action_is_supported(self) -> None:
        response = self.client.post('/api/control', json={'action': 'ack'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])


if __name__ == '__main__':
    unittest.main()
