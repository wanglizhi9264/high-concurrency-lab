"""Provision two fixed business DBs without deleting existing data or printing credentials."""

import re
import subprocess

from concurrency_lab.core.config import Settings
from concurrency_lab.db.business import BUSINESS_DATABASES


def main() -> None:
    user = Settings().mysql_user
    if re.fullmatch(r"[A-Za-z0-9_]{1,32}", user) is None:
        raise ValueError("Provisioning requires an alphanumeric local MySQL username")
    statements = []
    for database in sorted(BUSINESS_DATABASES):
        statements.extend(
            [
                f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4;",
                f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{user}'@'%';",
            ]
        )
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "mysql",
            "sh",
            "-c",
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot',
        ],
        input="\n".join(statements),
        text=True,
        check=True,
    )
    print("Fixed business databases provisioned; existing data retained.")


if __name__ == "__main__":
    main()
