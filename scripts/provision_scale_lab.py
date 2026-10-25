"""Create/grant only literal009databases in an explicit experiment Compose project."""

import argparse
import os
import re
import subprocess

from concurrency_lab.experiments.scale.safety import DATABASES


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-name", default=os.getenv("COMPOSE_PROJECT_NAME", "high-concurrency-lab")
    )
    arguments = parser.parse_args()
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", arguments.project_name) is None:
        parser.error("Use a bounded Compose project name")
    statements = ["GRANT SELECT ON mysql.innodb_index_stats TO 'lab_exp'@'%';"]
    for database in sorted(DATABASES):
        statements += [
            f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4;",
            f"GRANT ALL PRIVILEGES ON `{database}`.* TO 'lab_exp'@'%';",
        ]
    subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            arguments.project_name,
            "-f",
            "compose.yaml",
            "-f",
            "compose.experiments.yaml",
            "--profile",
            "experiments",
            "exec",
            "-T",
            "mysql-experiment",
            "sh",
            "-c",
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot',
        ],
        input="\n".join(statements),
        text=True,
        check=True,
    )
    print("Fixed009databases provisioned; existing data retained.")


if __name__ == "__main__":
    main()
