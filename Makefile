CXX ?= c++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -pedantic
CPPFLAGS += -Iinclude

SOURCES := src/core.cpp src/algorithms.cpp src/main.cpp
TARGET := bin/mwhc

.PHONY: all clean test case-studies

all: $(TARGET)

$(TARGET): $(SOURCES) include/mwhc.hpp
	@mkdir -p bin
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(SOURCES) -o $@

test: $(TARGET)
	python3 tests/smoke_test.py

case-studies:
	python3 case_studies/build_enron_case_study_gexf.py
	python3 case_studies/build_davis_community_case_gexf.py

clean:
	rm -rf bin case_studies/output
