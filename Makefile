CC = gcc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
PYTHON ?= python3
TARGET = circuit_calculator

.PHONY: all test clean

all: $(TARGET)

$(TARGET): circuit_calculator.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) $(LDLIBS) -o $@

test: $(TARGET)
	$(PYTHON) tests/test_calculator.py ./$(TARGET)

clean:
	$(RM) $(TARGET)
