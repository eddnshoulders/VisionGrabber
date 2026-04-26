################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
CPP_SRCS += \
../Core/Test/CommandParser_test.cpp \
../Core/Test/CoreXY_test.cpp \
../Core/Test/Machine_test.cpp \
../Core/Test/Servo_test.cpp \
../Core/Test/Stepper_test.cpp \
../Core/Test/TMC2209_test.cpp 

OBJS += \
./Core/Test/CommandParser_test.o \
./Core/Test/CoreXY_test.o \
./Core/Test/Machine_test.o \
./Core/Test/Servo_test.o \
./Core/Test/Stepper_test.o \
./Core/Test/TMC2209_test.o 

CPP_DEPS += \
./Core/Test/CommandParser_test.d \
./Core/Test/CoreXY_test.d \
./Core/Test/Machine_test.d \
./Core/Test/Servo_test.d \
./Core/Test/Stepper_test.d \
./Core/Test/TMC2209_test.d 


# Each subdirectory must supply rules for building sources it contributes
Core/Test/%.o Core/Test/%.su Core/Test/%.cyclo: ../Core/Test/%.cpp Core/Test/subdir.mk
	arm-none-eabi-g++ "$<" -mcpu=cortex-m3 -std=gnu++14 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F103xE -c -I../Core/Inc -I../Drivers/STM32F1xx_HAL_Driver/Inc/Legacy -I../Drivers/STM32F1xx_HAL_Driver/Inc -I../Drivers/CMSIS/Device/ST/STM32F1xx/Include -I../Drivers/CMSIS/Include -O0 -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti -fno-use-cxa-atexit -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Core-2f-Test

clean-Core-2f-Test:
	-$(RM) ./Core/Test/CommandParser_test.cyclo ./Core/Test/CommandParser_test.d ./Core/Test/CommandParser_test.o ./Core/Test/CommandParser_test.su ./Core/Test/CoreXY_test.cyclo ./Core/Test/CoreXY_test.d ./Core/Test/CoreXY_test.o ./Core/Test/CoreXY_test.su ./Core/Test/Machine_test.cyclo ./Core/Test/Machine_test.d ./Core/Test/Machine_test.o ./Core/Test/Machine_test.su ./Core/Test/Servo_test.cyclo ./Core/Test/Servo_test.d ./Core/Test/Servo_test.o ./Core/Test/Servo_test.su ./Core/Test/Stepper_test.cyclo ./Core/Test/Stepper_test.d ./Core/Test/Stepper_test.o ./Core/Test/Stepper_test.su ./Core/Test/TMC2209_test.cyclo ./Core/Test/TMC2209_test.d ./Core/Test/TMC2209_test.o ./Core/Test/TMC2209_test.su

.PHONY: clean-Core-2f-Test

