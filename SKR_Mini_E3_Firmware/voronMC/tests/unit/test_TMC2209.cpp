#include <gtest/gtest.h>
#include "MockUART.h"
#include "TMC2209.h"
#include "Config.h"
#include <cstdint>

// ── constants ─────────────────────────────────────────────────────────────────
static constexpr uint8_t SYNC_BYTE    = 0x05;
static constexpr uint8_t WRITE_BIT    = 0x80;

static constexpr uint8_t REG_GCONF      = 0x00;
static constexpr uint8_t REG_IFCNT      = 0x02;
static constexpr uint8_t REG_IHOLD_IRUN = 0x10;
static constexpr uint8_t REG_TPOWERDOWN = 0x11;
static constexpr uint8_t REG_TCOOLTHRS  = 0x14;
static constexpr uint8_t REG_CHOPCONF   = 0x6C;
static constexpr uint8_t REG_SGTHRS     = 0x40;

// ── helpers ───────────────────────────────────────────────────────────────────

static uint32_t decodeData(const std::vector<uint8_t>& msg)
{
    return ((uint32_t)msg[3] << 24) |
           ((uint32_t)msg[4] << 16) |
           ((uint32_t)msg[5] << 8)  |
           ((uint32_t)msg[6]);
}

static std::vector<uint8_t> buildReadResponse(TMC2209& tmc,
                                               uint8_t reg,
                                               uint32_t value)
{
    std::vector<uint8_t> resp(8);
    resp[0] = SYNC_BYTE;
    resp[1] = 0xFF;
    resp[2] = reg;
    resp[3] = (value >> 24) & 0xFF;
    resp[4] = (value >> 16) & 0xFF;
    resp[5] = (value >> 8)  & 0xFF;
    resp[6] = (value >> 0)  & 0xFF;
    resp[7] = tmc.calcCRC(resp.data(), 7);
    return resp;
}

// ── fixture ───────────────────────────────────────────────────────────────────

class TMC2209Test : public ::testing::Test {
protected:
    MockUART mockuart;
    TMC2209  tmc;

    static constexpr uint8_t SLAVE_ADDR = 0x00;

    TMC2209Test()
        : tmc(mockuart, SLAVE_ADDR)
    {}

    // load one IFCNT read pair for verifyWrite (before=n, after=n+1)
    void loadIFCNTPair(uint8_t n) {
        auto before = buildReadResponse(tmc, REG_IFCNT, n);
        auto after  = buildReadResponse(tmc, REG_IFCNT, n + 1);
        mockuart.loadRxBuffer(before.data(), before.size());
        mockuart.loadRxBuffer(after.data(),  after.size());
    }

    // load all UART responses needed for a full init() call:
    // 1x isConnected read + 6x verifyWrite pairs
    void loadInitResponses() {
        // isConnected reads IFCNT once
        auto ifcnt = buildReadResponse(tmc, REG_IFCNT, 1);
        mockuart.loadRxBuffer(ifcnt.data(), ifcnt.size());

        // verifyWrite for each of the 6 registers
        for (int i = 0; i < 6; i++) {
            loadIFCNTPair(i);
        }
    }
};

// ── CRC ───────────────────────────────────────────────────────────────────────

TEST_F(TMC2209Test, CRCDeterministic)
{
    uint8_t data[] = {0x05, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00};
    EXPECT_EQ(tmc.calcCRC(data, 7), tmc.calcCRC(data, 7));
}

TEST_F(TMC2209Test, CRCChangesWithData)
{
    uint8_t data_a[] = {0x05, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00};
    uint8_t data_b[] = {0x05, 0x00, 0x80, 0x00, 0x00, 0x00, 0x01};
    EXPECT_NE(tmc.calcCRC(data_a, 7), tmc.calcCRC(data_b, 7));
}

TEST_F(TMC2209Test, CRCChangesWithRegister)
{
    uint8_t data_a[] = {0x05, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00};
    uint8_t data_b[] = {0x05, 0x00, 0x90, 0x00, 0x00, 0x00, 0x00};
    EXPECT_NE(tmc.calcCRC(data_a, 7), tmc.calcCRC(data_b, 7));
}

TEST_F(TMC2209Test, CRCChangesWithSlaveAddress)
{
    uint8_t data_a[] = {0x05, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00};
    uint8_t data_b[] = {0x05, 0x01, 0x80, 0x00, 0x00, 0x00, 0x00};
    EXPECT_NE(tmc.calcCRC(data_a, 7), tmc.calcCRC(data_b, 7));
}

// ── datagram format ───────────────────────────────────────────────────────────

TEST_F(TMC2209Test, WriteDatagramSyncByte)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);
    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    EXPECT_EQ(msg[0], SYNC_BYTE);
}

TEST_F(TMC2209Test, WriteDatagramSlaveAddress)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);
    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    EXPECT_EQ(msg[1], SLAVE_ADDR);
}

TEST_F(TMC2209Test, WriteDatagramHasWriteBit)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);
    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    EXPECT_TRUE(msg[2] & WRITE_BIT);
}

TEST_F(TMC2209Test, WriteDatagramCRCValid)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);
    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    uint8_t expected_crc = tmc.calcCRC(msg.data(), 7);
    EXPECT_EQ(msg[7], expected_crc);
}

// ── GCONF register ────────────────────────────────────────────────────────────

TEST_F(TMC2209Test, GCONFEnSpreadcycleSet)
{
    loadInitResponses();
    TMC2209Config cfg = TMC2209_CFG_XY;
    cfg.en_spreadcycle = true;
    tmc.init(cfg);

    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    uint32_t gconf = decodeData(msg);
    EXPECT_TRUE(gconf & (1UL << 2));
}

TEST_F(TMC2209Test, GCONFEnSpreadcycleClear)
{
    loadInitResponses();
    TMC2209Config cfg = TMC2209_CFG_XY;
    cfg.en_spreadcycle = false;
    tmc.init(cfg);

    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    uint32_t gconf = decodeData(msg);
    EXPECT_FALSE(gconf & (1UL << 2));
}

TEST_F(TMC2209Test, GCONFPdnDisableSet)
{
    loadInitResponses();
    TMC2209Config cfg = TMC2209_CFG_XY;
    cfg.pdn_disable = true;
    tmc.init(cfg);

    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    uint32_t gconf = decodeData(msg);
    EXPECT_TRUE(gconf & (1UL << 6));
}

TEST_F(TMC2209Test, GCONFMstepRegSelectSet)
{
    loadInitResponses();
    TMC2209Config cfg = TMC2209_CFG_XY;
    cfg.mstep_reg_select = true;
    tmc.init(cfg);

    auto msg = mockuart.findWriteForReg(REG_GCONF);
    ASSERT_FALSE(msg.empty());
    uint32_t gconf = decodeData(msg);
    EXPECT_TRUE(gconf & (1UL << 7));
}

// ── IHOLD_IRUN register ───────────────────────────────────────────────────────

TEST_F(TMC2209Test, IHoldIRunRunCurrent)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_IHOLD_IRUN);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    uint8_t run_current = (val >> 8) & 0x1F;
    EXPECT_EQ(run_current, TMC2209_CFG_XY.run_current);
}

TEST_F(TMC2209Test, IHoldIRunHoldCurrent)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_IHOLD_IRUN);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    uint8_t hold_current = val & 0x1F;
    EXPECT_EQ(hold_current, TMC2209_CFG_XY.hold_current);
}

TEST_F(TMC2209Test, IHoldIRunIholdDelay)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_IHOLD_IRUN);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    uint8_t ihold_delay = (val >> 16) & 0x0F;
    EXPECT_EQ(ihold_delay, TMC2209_CFG_XY.ihold_delay);
}

// ── CHOPCONF register ─────────────────────────────────────────────────────────

TEST_F(TMC2209Test, CHOPCONFMicrostepBits)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_CHOPCONF);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    uint8_t mres = (val >> 24) & 0x0F;
    EXPECT_EQ(mres, 3);  // 32 microsteps = MRES bits = 3
}

TEST_F(TMC2209Test, CHOPCONFDefaultBitsPreserved)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_CHOPCONF);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    // lower 24 bits should match defaults 0x10000053 with MRES cleared
    EXPECT_EQ(val & 0x00FFFFFF, 0x00000053);
}

// ── TPOWERDOWN register ───────────────────────────────────────────────────────

TEST_F(TMC2209Test, TPOWERDOWNValue)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_TPOWERDOWN);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    EXPECT_EQ(val, TMC2209_CFG_XY.tpowerdown);
}

// ── TCOOLTHRS register ────────────────────────────────────────────────────────

TEST_F(TMC2209Test, TCOOLTHRSValue)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_TCOOLTHRS);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    EXPECT_EQ(val, TMC2209_CFG_XY.tcool_threshold);
}

// ── SGTHRS register ───────────────────────────────────────────────────────────

TEST_F(TMC2209Test, SGTHRSValue)
{
    loadInitResponses();
    tmc.init(TMC2209_CFG_XY);

    auto msg = mockuart.findWriteForReg(REG_SGTHRS);
    ASSERT_FALSE(msg.empty());
    uint32_t val = decodeData(msg);
    EXPECT_EQ(val & 0xFF, TMC2209_CFG_XY.sg_threshold);
}

// ── isConnected ───────────────────────────────────────────────────────────────

TEST_F(TMC2209Test, IsConnectedReturnsTrueOnValidResponse)
{
    auto resp = buildReadResponse(tmc, 0x02, 1);
    mockuart.loadRxBuffer(resp.data(), resp.size());
    EXPECT_TRUE(tmc.isConnected());
}

TEST_F(TMC2209Test, IsConnectedReturnsFalseOnTimeout)
{
    // no rx buffer loaded -- UART_Receive returns IUART_TIMEOUT
    EXPECT_FALSE(tmc.isConnected());
}
