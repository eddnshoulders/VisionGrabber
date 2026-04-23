/*
 * GPIOImp.cpp
 *
 *  Created on: 5 Apr 2026
 *      Author: f402n
 */

#include <HALImp/GPIOImp.h>
#include <cstring>


GPIOImp::GPIOImp(GPIO_TypeDef* port, uint16_t pin)
						: port_(port),
						  pin_(pin) {}

void GPIOImp::setPin(void) { HAL_GPIO_WritePin(port_, pin_, GPIO_PIN_SET); }
void GPIOImp::resetPin(void) { HAL_GPIO_WritePin(port_, pin_, GPIO_PIN_RESET); }
bool GPIOImp::readPin(void) { return (bool)HAL_GPIO_ReadPin(port_, pin_); }
void GPIOImp::togglePin(void) {	HAL_GPIO_TogglePin(port_, pin_); }
IGPIO_StatusTypeDef GPIOImp::lockPin() { return (IGPIO_StatusTypeDef)HAL_GPIO_LockPin(port_, pin_); }

//void HAL_GPIO_EXTI_IRQHandler(uint16_t GPIO_Pin);
//void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin);

GPIOImp::~GPIOImp(void) = default;
