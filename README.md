# Runce

# 🚀 The One-and-Done Process Wrangler

> _"Runce and done! No repeats, no retreats!"_ 🏃‍♂️💨  
> 🔒 **Guaranteed Singleton Execution** • 📊 **Process Tracking** • ⏱️ **Lifecycle Management**

[![runce](icon.png)](https://github.com/jet-logic/runce)
[![PyPI version fury.io](https://badge.fury.io/py/runce.svg)](https://pypi.python.org/pypi/runce/)

## ☕ Support

If you find this project helpful, consider supporting me:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/B0B01E8SY7)

## Features ✨

- 🚫 **No Duplicates**: Each command runs exactly once per unique ID
- 📝 **Process Tracking**: View all managed processes with status
- ⏱️ **Execution Time**: Track how long processes have been running
- 📂 **Log Management**: Automatic stdout/stderr capture
- 🛑 **Clean Termination**: Proper process killing

## Installation 📦

```bash
pip install runce
```

## Usage

```
runce <command> [options] [arguments]
```

## Commands

### `run`

Runs a new singleton process.

```
runce run [options] ARG...
```

**Options:**

- `--id <run_id>`: Unique run identifier (required).
- `--working-directory <cwd>`: Working directory for the command.
- `-t <tail>` / `--tail <tail>`: Tail the output (n lines). Use `-t -1` to print the entire output.
- `--overwrite`: Overwrite existing entry if it exists.
- `--run-after <command>`: Run a command after the main command finishes.

**Example:**

```bash
runce run --id my-unique-task sleep 60
```

### `ls` / `list`

Lists all managed processes.

```bash
runce ls [options]
```

**Options:**

- `-f <format>` / `--format <format>`: Format of the output line (see examples below).

**Example:**

```bash
runce ls
runce ls -f "{pid}\t{name}\t{command}"
```

### `status`

Checks the status of processes.

```bash
runce status [options] [ID...]
```

**Options:**

- `-f <format>` / `--format <format>`: Format of the output line.

**Example:**

```bash
runce status my-unique-task
```

### `kill`

Kills running processes.

```bash
runce kill [options] ID...
```

**Options:**

- `--dry-run`: Perform a dry run (don't actually kill).
- `--remove`: Remove the entry after killing.

**Example:**

```bash
runce kill my-unique-task
```

### `clean`

Cleans up entries for non-existing processes.

```bash
runce clean [ID...]
```

**Example:**

```bash
runce clean
```

### `tail`

Tails the output of processes.

```bash
runce tail [options] [ID...]
```

**Options:**

- `-n <lines>` / `--lines <lines>`: Number of lines to tail.
- `--header <format>`: Header format.
- `-x` / `--only-existing`: Only show existing processes.
- `-t` / `--tab`: Prefix tab space to each line.

**Example:**

```bash
runce tail my-unique-task
runce tail -n 20 my-unique-task
```

### `restart`

Restarts a process.

```bash
runce restart [options] ID...
```

**Options:**

- `-t <tail>` / `--tail <tail>`: Tail the output after restarting.

**Example:**

```bash
runce restart my-unique-task
```

## Examples 💡

### 1. Running a Background Service

```bash
runce run --id api-server -- python api.py
```

### 2. Checking Live Processes

```bash
$ runce list
PID     NAME        STATUS      ELAPSED    COMMAND
1234    api-server  ✅ Live  01:23:45   python api.py
5678    worker      ❌ Gone  00:45:30   python worker.py
```

### 3. Preventing Duplicates

```bash
$ runce run --id daily-job -- python daily.py
🚀 Started: PID:5678(✅ Live) daily-job

$ runce run --id daily-job -- python daily.py
🚨 Already running: PID:5678(✅ Live) daily-job
```

## Formats

The `-f` / `--format` option in the `ls` and `status` commands allows you to customize the output format. You can use the following placeholders:

- `{pid}`: Process ID
- `{name}`: Run ID / Name
- `{pid_status}`: Process status ("✅ Live" or "👻 Gone")
- `{elapsed}`: Elapsed time
- `{command}`: The command being executed

## How It Works

RunCE stores process information in JSON files within a temporary directory (`/tmp/runce.v1` on Linux). Before starting a new process, it checks for existing entries with the same ID to prevent duplicates.

## Development 🏗️

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Lint code
flake8 runce
```

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
