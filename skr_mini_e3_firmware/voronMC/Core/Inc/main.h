/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f1xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define XSTOP_Pin GPIO_PIN_0
#define XSTOP_GPIO_Port GPIOC
#define XSTOP_EXTI_IRQn EXTI0_IRQn
#define YSTOP_Pin GPIO_PIN_1
#define YSTOP_GPIO_Port GPIOC
#define YSTOP_EXTI_IRQn EXTI1_IRQn
#define ZSTOP_Pin GPIO_PIN_2
#define ZSTOP_GPIO_Port GPIOC
#define ZSTOP_EXTI_IRQn EXTI2_IRQn
#define SERVO_Pin GPIO_PIN_1
#define SERVO_GPIO_Port GPIOA
#define RPI_TX_Pin GPIO_PIN_2
#define RPI_TX_GPIO_Port GPIOA
#define RPI_RX_Pin GPIO_PIN_3
#define RPI_RX_GPIO_Port GPIOA
#define ZDIR_Pin GPIO_PIN_5
#define ZDIR_GPIO_Port GPIOC
#define ZSTEP_Pin GPIO_PIN_0
#define ZSTEP_GPIO_Port GPIOB
#define ZEN_Pin GPIO_PIN_1
#define ZEN_GPIO_Port GPIOB
#define BDIR_Pin GPIO_PIN_2
#define BDIR_GPIO_Port GPIOB
#define BSTEP_Pin GPIO_PIN_10
#define BSTEP_GPIO_Port GPIOB
#define BEN_Pin GPIO_PIN_11
#define BEN_GPIO_Port GPIOB
#define ADIR_Pin GPIO_PIN_12
#define ADIR_GPIO_Port GPIOB
#define ASTEP_Pin GPIO_PIN_13
#define ASTEP_GPIO_Port GPIOB
#define AEN_Pin GPIO_PIN_14
#define AEN_GPIO_Port GPIOB
#define FAN_Pin GPIO_PIN_6
#define FAN_GPIO_Port GPIOC
#define BED_Pin GPIO_PIN_9
#define BED_GPIO_Port GPIOC
#define TMC_UART_TX_Pin GPIO_PIN_10
#define TMC_UART_TX_GPIO_Port GPIOC
#define TMC_UART_RX_Pin GPIO_PIN_11
#define TMC_UART_RX_GPIO_Port GPIOC

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
