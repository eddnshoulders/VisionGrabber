/*
 * CommandParser.cpp
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

// CommandParser.cpp
#include "CommandParser.h"
#include <cstdio>
#include <cctype>
#include <cstdlib>

CommandParser::CommandParser(void)
	: len_(0)
{
	memset(buf_, 0, sizeof(buf_));
	memset(&parsed_, 0, sizeof(parsed_));
}

bool CommandParser::processByte(uint8_t byte)
{
    if (byte == '\r') return false;  // ignore CR

    if (byte == '\n') {
        buf_[len_] = '\0';
        bool result = parseLine();
        return result;
    }

    if (len_ < CMD_BUFFER_SIZE - 1) {
        buf_[len_++] = static_cast<char>(byte);
    }
    // silently drop bytes if buffer full

    return false;
}

ParsedCommand CommandParser::getCommand(void) {
	ParsedCommand parsed = parsed_;
	reset();
	return parsed;		// returns last parsed commmand
}


void CommandParser::reset(void)
{
    len_ = 0;
    memset(&parsed_, 0, sizeof(parsed_));
}

bool CommandParser::parseLine(void)
{
    if (len_ == 0) return false;

    // Convert to uppercase
    for (uint8_t i = 0; i < len_; i++) {
        buf_[i] = toupper(buf_[i]);
    }

    // Extract command word (e.g. G28, G0, M400)
    uint8_t i = 0;
    uint8_t cmd_len = 0;
    while (i < len_ && !isspace(buf_[i]) && cmd_len < 7) {
        parsed_.cmd[cmd_len++] = buf_[i++];
    }
    parsed_.cmd[cmd_len] = '\0';

    // Parse parameters
    while (i < len_) {
    	while (i < len_ && isspace(buf_[i])) i++;  // skip whitespace
        if (i >= len_) break;

        char param = buf_[i++];
        float value = 0.0f;
        // Parse the float value after the parameter letter
        uint8_t start = i;
        while (i < len_ && (isdigit(buf_[i]) || buf_[i] == '.' || buf_[i] == '-')) i++;

        if (i < len_ && !isspace(buf_[i])) {
        	parsed_.error = true;
        	return false;
        }

        if (i > start) {
            // Extract substring and convert
            char tmp[16] = {0};
            memcpy(tmp, &buf_[start], i - start);
            value = atof(tmp);
        }

        switch (param) {
            case 'X': parsed_.x = value; parsed_.has_x = true; break;
            case 'Y': parsed_.y = value; parsed_.has_y = true; break;
            case 'Z': parsed_.z = value; parsed_.has_z = true; break;
            case 'F': parsed_.f = value; parsed_.has_f = true; break;
            case 'S': parsed_.s = value; parsed_.has_s = true; break;
            case 'P': parsed_.p = value; parsed_.has_p = true; break;
            default: break;  // ignore unknown parameters
        }
    }

    return true;
}

CommandParser::~CommandParser() = default;


