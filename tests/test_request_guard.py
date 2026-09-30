"""The authoring interface refuses requests a browser was tricked into making.

Exercised through the real Flask app, so what is tested is what the service
does, not what the guard module would do if it were installed. The unsafe
request used throughout is erasing a film that does not exist: when allowed
through it redirects back to the catalogue with an error and changes nothing,
so a refusal (403) and an admission (302) are unmistakable and harmless.
"""
import os
import unittest
from unittest import mock

import request_guard
from app import app

BOUND = "100.64.0.9"
PORT = "11914"
ORIGIN = f"http://{BOUND}:{PORT}"


class GuardTest(unittest.TestCase):
    def setUp(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("KINO_")}
        env.update({"KINO_HOST": BOUND, "KINO_PORT": PORT})
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app.test_client()

    def post(self, headers=None, host=f"{BOUND}:{PORT}"):
        return self.client.post("/erase/no-such-film", base_url=f"http://{host}",
                                headers=headers or {})


class CrossSiteRequests(GuardTest):
    def test_a_cross_site_post_is_refused(self):
        response = self.post({"Origin": "https://evil.example",
                              "Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 403)

    def test_a_foreign_origin_alone_is_refused(self):
        self.assertEqual(self.post({"Origin": "https://evil.example"}).status_code, 403)

    def test_another_tailnet_host_is_refused(self):
        # Every tailnet host is the "same site"; that is exactly the case to stop.
        response = self.post({"Origin": "http://100.64.0.10:8080",
                              "Sec-Fetch-Site": "same-site"})
        self.assertEqual(response.status_code, 403)

    def test_a_null_origin_is_refused(self):
        self.assertEqual(self.post({"Origin": "null"}).status_code, 403)


class SameOriginRequests(GuardTest):
    def test_a_same_origin_post_is_admitted(self):
        response = self.post({"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(response.status_code, 302)

    def test_origin_alone_is_enough(self):
        self.assertEqual(self.post({"Origin": ORIGIN}).status_code, 302)

    def test_sec_fetch_site_alone_is_enough(self):
        self.assertEqual(self.post({"Sec-Fetch-Site": "same-origin"}).status_code, 302)

    def test_reads_need_no_headers(self):
        response = self.client.get("/films", base_url=ORIGIN)
        self.assertEqual(response.status_code, 200)


class HeaderlessRequests(GuardTest):
    def test_a_post_with_neither_header_is_refused_by_default(self):
        self.assertEqual(self.post().status_code, 403)

    def test_the_legacy_flag_admits_it(self):
        with mock.patch.dict(os.environ, {"KINO_ALLOW_LEGACY_CLIENTS": "1"}):
            self.assertEqual(self.post().status_code, 302)

    def test_the_legacy_flag_never_admits_a_cross_site_post(self):
        with mock.patch.dict(os.environ, {"KINO_ALLOW_LEGACY_CLIENTS": "1"}):
            self.assertEqual(self.post({"Sec-Fetch-Site": "cross-site"}).status_code, 403)


class HostAllowlist(GuardTest):
    def test_a_rebound_host_is_refused_even_for_a_read(self):
        response = self.client.get("/films", base_url=f"http://evil.example:{PORT}")
        self.assertEqual(response.status_code, 403)

    def test_a_rebound_host_is_refused_for_a_same_origin_post(self):
        # The attacker's page IS same-origin with evil.example after rebinding;
        # only the Host header gives it away.
        host = f"evil.example:{PORT}"
        response = self.post({"Origin": f"http://{host}",
                              "Sec-Fetch-Site": "same-origin"}, host=host)
        self.assertEqual(response.status_code, 403)

    def test_the_bound_address_on_another_port_is_refused(self):
        self.assertEqual(self.client.get("/films", base_url=f"http://{BOUND}:9999")
                         .status_code, 403)

    def test_loopback_is_allowed(self):
        for host in ("127.0.0.1:11914", "localhost:5000", "[::1]:11914", "localhost"):
            with self.subTest(host=host):
                self.assertEqual(self.client.get("/films", base_url=f"http://{host}")
                                 .status_code, 200)

    def test_the_operator_can_add_a_name(self):
        with mock.patch.dict(os.environ,
                             {"KINO_ALLOWED_HOSTS": "ppmanchester:11914, kino.tail.ts.net:11914"}):
            for host in ("ppmanchester:11914", "kino.tail.ts.net:11914"):
                with self.subTest(host=host):
                    self.assertEqual(self.client.get("/films", base_url=f"http://{host}")
                                     .status_code, 200)


class Parsing(unittest.TestCase):
    def test_split_host(self):
        self.assertEqual(request_guard.split_host("A.Example:80"), ("a.example", "80"))
        self.assertEqual(request_guard.split_host("[::1]:5"), ("[::1]", "5"))
        self.assertEqual(request_guard.split_host("[::1]"), ("[::1]", None))
        self.assertEqual(request_guard.split_host("host"), ("host", None))

    def test_a_wildcard_bind_names_no_address(self):
        self.assertEqual(request_guard.allowed_hosts("0.0.0.0", 1), set())


if __name__ == "__main__":
    unittest.main()
