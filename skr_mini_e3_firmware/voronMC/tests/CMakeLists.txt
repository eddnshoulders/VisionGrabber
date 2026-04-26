cmake_minimum_required(VERSION 3.16)
project(voronMC_tests)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")

include(CTest)

find_package(GTest REQUIRED)

add_executable(run_tests
    unit/test_CommandParser.cpp
    unit/test_Servo.cpp
    unit/test_Stepper.cpp
    unit/test_CoreXY.cpp
    unit/test_TMC2209.cpp
    unit/test_Machine.cpp
    ../Core/Src/CommandParser.cpp
    ../Core/Src/Servo.cpp
    ../Core/Src/Stepper.cpp
    ../Core/Src/CoreXY.cpp
    ../Core/Src/TMC2209.cpp
    ../Core/Src/Machine.cpp
)

target_include_directories(run_tests PRIVATE
    ${GTEST_INCLUDE_DIRS}
    ../Core/Inc
    mocks
)

target_link_libraries(run_tests
    GTest::GTest
    GTest::Main
)

include(GoogleTest)
gtest_discover_tests(run_tests)