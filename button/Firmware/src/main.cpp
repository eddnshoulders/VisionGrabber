#include <Arduino.h>

#define BUT_PIN        2
#define DEBOUNCE_MS    10    // sample every 10 ms
#define DEBOUNCE_STEPS 5    // require 10 consecutive stable low readings

const uint8_t ledPins[] = {5, 6, 9, 10};

// Debounce state
enum DebounceState { IDLE, SAMPLING };
volatile DebounceState dbState = IDLE;
unsigned long nextSampleTime = 0;
uint8_t stableCount = 0;

bool buttonPressed = false;   // consumed in loop

char rxBuf[32];
uint8_t rxPos = 0;

void buttonISR() {
  // Only kick off sampling if we're not already doing so
  if (dbState == IDLE) {
    dbState = SAMPLING;
    stableCount = 0;
  }
}

void setLEDs(uint8_t brightness) {
  for (uint8_t i = 0; i < 4; i++) {
    analogWrite(ledPins[i], brightness);
  }
}

void handleCommand(const char *cmd) {
  if (strcmp(cmd, "LED_OFF") == 0) {
    setLEDs(0);
  } else if (strcmp(cmd, "LED_ON") == 0) {
    setLEDs(255);
  } else if (strncmp(cmd, "LED:", 4) == 0) {
    int val = atoi(cmd + 4);
    val = constrain(val, 0, 255);
    setLEDs((uint8_t)val);
  }
}

void setup() {
  pinMode(BUT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(BUT_PIN), buttonISR, FALLING);

  for (uint8_t i = 0; i < 4; i++) {
    pinMode(ledPins[i], OUTPUT);
    analogWrite(ledPins[i], 0);
  }

  Serial.begin(115200);
  while (!Serial);
  delay(100);
}

void loop() {
  unsigned long now = millis();

  // --- Debounce state machine ---
  if (dbState == SAMPLING) {

    if (now >= nextSampleTime) {
      nextSampleTime = now + DEBOUNCE_MS;

      if (digitalRead(BUT_PIN) == LOW) {
        stableCount++;
        //Serial.print("stable count: ");
        //Serial.println(stableCount);

        if (stableCount >= DEBOUNCE_STEPS) {
          // Confirmed press - wait for release before accepting another
          buttonPressed = true;
          stableCount = 0;
          dbState = IDLE;

          // Re-arm ISR only on rising edge (release) to avoid re-triggering
          detachInterrupt(digitalPinToInterrupt(BUT_PIN));
          attachInterrupt(digitalPinToInterrupt(BUT_PIN), []() {
            // Switch released - re-arm for next press
            detachInterrupt(digitalPinToInterrupt(BUT_PIN));
            attachInterrupt(digitalPinToInterrupt(BUT_PIN), buttonISR, FALLING);
          }, RISING);

          Serial.println("BTN");
        }
      } else {
        // Pin went high mid-sequence - noise, reset
        //Serial.println("noise - resetting count");
        stableCount = 0;
        dbState = IDLE;  // wait for ISR to kick us again
      }
    }
  }

  // --- Consume button press ---
  if (buttonPressed) {
    buttonPressed = false;
    setLEDs(128);  // example action
  }

  // --- Non-blocking serial reader ---
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (rxPos > 0) {
        rxBuf[rxPos] = '\0';
        handleCommand(rxBuf);
        rxPos = 0;
      }
    } else {
      if (rxPos < sizeof(rxBuf) - 1) {
        rxBuf[rxPos++] = c;
      } else {
        rxPos = 0;
      }
    }
  }
}