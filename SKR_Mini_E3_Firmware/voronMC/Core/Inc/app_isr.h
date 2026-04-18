/*
 * app_isr.h
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#ifndef INC_APP_ISR_H_
#define INC_APP_ISR_H_

void app_tim1_update(void);
void app_tim2_update(void);
void app_tim8_update(void);

void app_on_xy_stall(void);
void app_on_z_endstop(void);

#endif /* INC_APP_ISR_H_ */
