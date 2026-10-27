#!/bin/bash
# Run one shard of upstream's valgrind test run inside the Pillow valgrind image:
# every <count>th test file, starting at <index> (1-based), so that each job
# stays inside the time a single fork run is allowed.
#   valgrind-shard.sh memcheck|leak <index> <count>
set -e
mode=$1
index=$2
count=$3

source /vpy3/bin/activate
cd /Pillow
make clean

files=$(find Tests -name "test_*.py" | sort | awk -v n="$count" -v i="$index" '(NR - 1) % n == i - 1')

if [ "$mode" = leak ]; then
    # as depends/docker-test-valgrind-memory.sh and the Makefile's valgrind-leak
    make install
    python3 -c "import pytest_valgrind" > /dev/null 2>&1 || python3 -m pip install pytest-valgrind
    PILLOW_VALGRIND_TEST=true PYTHONMALLOC=malloc valgrind --suppressions=Tests/oss-fuzz/python.supp \
        --leak-check=full --show-leak-kinds=definite --errors-for-leak-kinds=definite \
        --log-file=/tmp/valgrind-output \
        python3 -m pytest -vv --valgrind --valgrind-log=/tmp/valgrind-output $files
else
    # as the valgrind image's own depends/test.sh
    make install-coverage
    PYTHONMALLOC=malloc valgrind --suppressions=/depends/python.supp --leak-check=no \
        --log-file=/tmp/valgrind-output \
        python3 -m pytest --no-memcheck -vv --valgrind --valgrind-log=/tmp/valgrind-output $files
fi
