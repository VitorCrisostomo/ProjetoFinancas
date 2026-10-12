"""Verifica o contrato de rede e volumes com o parser oficial do Compose."""

import json
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


@unittest.skipUnless(os.getenv("FINANCEHUB_TEST_COMPOSE"), "Defina FINANCEHUB_TEST_COMPOSE.")
class DockerComposeTests(unittest.TestCase):
    def configuration(self, external=False):
        project = Path(__file__).resolve().parents[2]
        executable = os.environ["FINANCEHUB_TEST_COMPOSE"]
        command = [executable]
        if Path(executable).stem == "docker":
            command.append("compose")
        with TemporaryDirectory() as temporary:
            empty_env = Path(temporary) / "compose.env"
            empty_env.write_text("# Synthetic operational configuration\n", encoding="utf-8")
            command += ["--profile", "tools"]
            command += [
                "--env-file",
                str(empty_env),
                "-f",
                str(project / "deploy/docker/compose.yaml"),
            ]
            if external:
                command += ["-f", str(project / "deploy/docker/compose.external.yaml")]
            command += ["config", "--format", "json"]
            environment = {
                **os.environ,
                "APP_HOST": "finance.fixture.ts.net",
                "FINANCEHUB_STATE_ROOT": str(Path(temporary) / "synthetic-state"),
                "FINANCEHUB_EXTERNAL_BACKUP_DIR": str(Path(temporary) / "synthetic-external"),
                "FINANCEHUB_SUBNET": "172.30.84.0/29",
                "FINANCEHUB_GATEWAY": "172.30.84.1",
                "FINANCEHUB_API_IP": "172.30.84.2",
                "FINANCEHUB_WEB_IP": "172.30.84.3",
            }
            result = subprocess.run(
                command,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_only_the_web_port_is_published_and_backup_has_no_network(self):
        config = self.configuration()
        services = config["services"]
        self.assertFalse(services["api"].get("ports"))
        self.assertEqual(services["web"]["ports"][0]["host_ip"], "127.0.0.1")
        for service in ("backup", "bootstrap", "maintenance"):
            self.assertEqual(services[service]["network_mode"], "none")
            self.assertFalse(services[service].get("ports"))
        self.assertEqual(services["api"]["environment"]["FINANCEHUB_DOCKER_PROXY"], "172.30.84.3")
        self.assertEqual(services["web"]["networks"]["application"]["ipv4_address"], "172.30.84.3")
        self.assertEqual(services["web"]["depends_on"]["api"]["condition"], "service_healthy")

    def test_container_permissions_and_mounts_keep_secrets_out_of_web_and_environment(self):
        services = self.configuration()["services"]
        self.assertFalse(services["web"].get("volumes"))
        for name, service in services.items():
            self.assertTrue(service["read_only"], name)
            self.assertEqual(service["cap_drop"], ["ALL"])
            self.assertIn("no-new-privileges:true", service["security_opt"])
            self.assertNotEqual(service["user"].split(":")[0], "0")
            self.assertFalse(service.get("env_file"))
            self.assertFalse(any("docker.sock" in v["target"] for v in service.get("volumes", [])))
            self.assertNotIn("JWT_SECRET_KEY", service.get("environment", {}))
            self.assertNotIn("PLUGGY_CLIENT_SECRET", service.get("environment", {}))
        for name in ("api", "backup", "maintenance"):
            mounts = {v["target"]: v for v in services[name]["volumes"]}
            self.assertTrue(mounts["/state/keys"]["read_only"])
            self.assertFalse(mounts["/state/config"].get("read_only", False))
            self.assertNotIn("/state/config/app.env", mounts)
            self.assertTrue(all(v["type"] == "bind" for v in mounts.values()))
            self.assertTrue(
                all(v.get("bind", {}).get("create_host_path") is False for v in mounts.values())
            )

    def test_external_override_adds_the_destination_to_backup_and_maintenance(self):
        services = self.configuration(external=True)["services"]
        for name in ("backup", "maintenance"):
            mounts = {v["target"]: v for v in services[name]["volumes"]}
            self.assertIn("/external-backups", mounts)
            self.assertTrue(mounts["/state/keys"]["read_only"])
            self.assertFalse(mounts["/external-backups"]["bind"]["create_host_path"])
        self.assertIn("--external-directory", services["backup"]["command"])


if __name__ == "__main__":
    unittest.main()
