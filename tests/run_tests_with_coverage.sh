#!/bin/bash
# Clean previous coverage data
rm -f /tmp/.coverage*
rm -rf /tmp/runce_coverage

# Run tests with coverage
python -m pytest tests/ \
  --cov=runce \
  --cov-append \
  --cov-report=term-missing

# Combine all coverage data
python -m coverage combine

# Generate HTML report in /tmp
python -m coverage html \
  --directory=/tmp/runce_coverage \
  --title="RunCE Coverage Report"

echo "Coverage report generated at: /tmp/runce_coverage/index.html"