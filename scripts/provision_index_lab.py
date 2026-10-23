"""Provision only fixed experiment databases; never clear or drop anything."""

import argparse
import subprocess

DATABASES = [f"concurrency_lab_exp_002_{size}" for size in (10000, 100000, 1000000)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", default="high-concurrency-lab")
    args = parser.parse_args()
    statements = ["GRANT SELECT ON mysql.innodb_index_stats TO 'lab_exp'@'%';"]
    for name in DATABASES:
        statements.extend(
            [
                f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4;",
                f"GRANT ALL PRIVILEGES ON `{name}`.* TO 'lab_exp'@'%';",
            ]
        )
    subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            args.project_name,
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
    print("Provisioned fixed experiment databases (existing data untouched).")


if __name__ == "__main__":
    main()
