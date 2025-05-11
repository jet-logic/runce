#!/bin/bash
NAME=runce
DOCS=/tmp/"$NAME"_coverage
export COVERAGE_FILE=/tmp/."$NAME"_coverage
echo [$NAME] $DOCS
rm -vf "$COVERAGE_FILE"*
rm -vrf $DOCS

# Run tests with coverage
python -m pytest tests/ \
  --cov=$NAME \
  --cov-append \
  --cov-report=term-missing

# Combine all coverage data
python -m coverage combine

# Generate HTML report in /tmp
python -m coverage html \
  --directory="$DOCS" \
  --title="$NAME Coverage Report"

echo "Coverage report generated at: $DOCS/index.html"