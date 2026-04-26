################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (14.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
CPP_SRCS += \
../Core/Src/HALImp/GPIOImp.cpp \
../Core/Src/HALImp/SYSImp.cpp \
../Core/Src/HALImp/TimerImp.cpp \
../Core/Src/HALImp/UARTImp.cpp 

OBJS += \
./Core/Src/HALImp/GPIOImp.o \
./Core/Src/HALImp/SYSImp.o \
./Core/Src/HALImp/TimerImp.o \
./Core/Src/HALImp/UARTImp.o 

CPP_DEPS += \
./Core/Src/HALImp/GPIOImp.d \
./Core/Src/HALImp/SYSImp.d \
./Core/Src/HALImp/TimerImp.d \
./Core/Src/HALImp/UARTImp.d 


# Each subdirectory must supply rules for building sources it contributes
Core/Src/HALImp/%.o Core/Src/HALImp/%.su Core/Src/HALImp/%.cyclo: ../Core/Src/HALImp/%.cpp Core/Src/HALImp/subdir.mk
	arm-none-eabi-g++ "$<" -mcpu=cortex-m3 -std=gnu++14 -DUSE_HAL_DRIVER -DSTM32F103xE -c -I../Core/Inc -I../Drivers/STM32F1xx_HAL_Driver/Inc/Legacy -I../Drivers/STM32F1xx_HAL_Driver/Inc -I../Drivers/CMSIS/Device/ST/STM32F1xx/Include -I../Drivers/CMSIS/Include -Os -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti -fno-use-cxa-atexit -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-Core-2f-Src-2f-HALImp

clean-Core-2f-Src-2f-HALImp:
	-$(RM) ./Core/Src/HALImp/GPIOImp.cyclo ./Core/Src/HALImp/GPIOImp.d ./Core/Src/HALImp/GPIOImp.o ./Core/Src/HALImp/GPIOImp.su ./Core/Src/HALImp/SYSImp.cyclo ./Core/Src/HALImp/SYSImp.d ./Core/Src/HALImp/SYSImp.o ./Core/Src/HALImp/SYSImp.su ./Core/Src/HALImp/TimerImp.cyclo ./Core/Src/HALImp/TimerImp.d ./Core/Src/HALImp/TimerImp.o ./Core/Src/HALImp/TimerImp.su ./Core/Src/HALImp/UARTImp.cyclo ./Core/Src/HALImp/UARTImp.d ./Core/Src/HALImp/UARTImp.o ./Core/Src/HALImp/UARTImp.su

.PHONY: clean-Core-2f-Src-2f-HALImp

