-- Minimal WoW API mock to exercise LegacyTracker under Lua 5.1: lua5.1 addon/test/harness.lua addon/LegacyTracker/LegacyTracker.lua
local now, timers, frames, printed = 1762300000, {}, {}, {}
local st = { name="Aldric", realm="ExampleRealm", class={"Warrior","WARRIOR"}, race={"Human","Human"}, level=11, xp=300, xpMax=8000,
  rested=6000, combat=false }
function time() return now end
function print(...) printed[#printed+1] = table.concat({...}, " ") end
function wipe(t) for k in pairs(t) do t[k]=nil end return t end
C_Timer = { After = function(d, cb) timers[#timers+1] = cb end }
function CreateFrame()
  local fr = { ev = {} }
  function fr:RegisterEvent(e) self.ev[e] = true end
  function fr:UnregisterEvent(e) self.ev[e] = nil end
  function fr:IsEventRegistered(e) return self.ev[e] or false end
  function fr:SetScript(_, h) self.h = h end
  frames[#frames+1] = fr
  return fr
end
ChatFrame1 = CreateFrame(); ChatFrame1:RegisterEvent("TIME_PLAYED_MSG"); NUM_CHAT_WINDOWS = 1
local addonFrame
function UnitName() return st.name end
function GetRealmName() return st.realm end
function UnitClass() return st.class[1], st.class[2] end
function UnitRace() return st.race[1], st.race[2] end
function UnitFactionGroup() return "Alliance" end
function UnitLevel() return st.level end
function UnitXP() return st.xp end
function UnitXPMax() return st.xpMax end
function GetXPExhaustion() return st.rested end
function GetRestState() return 1, "Rested", 2 end
function IsResting() return true end
function GetRealZoneText() return "Elwynn Forest" end
function GetSubZoneText() return "Goldshire" end
function GetMoney() return 12345 end
function InCombatLockdown() return st.combat end
function UnitAffectingCombat() return st.combat end
function GetProfessions() return 1, 2, nil, nil, nil end
function GetProfessionInfo(i) if i==1 then return "Mining", 0, 45, 75 end return "Blacksmithing", 0, 30, 75 end
function RequestTimePlayed() addonFrame.h(addonFrame, "TIME_PLAYED_MSG", 3600, 600) end
SlashCmdList = {}
local chunk = assert(loadfile(arg[1]))
chunk("LegacyTracker", {})
addonFrame = frames[#frames]
local function fire(e, ...) if addonFrame.ev[e] then addonFrame.h(addonFrame, e, ...) end end
local function run() while #timers > 0 do local t = table.remove(timers, 1); t() end end

fire("PLAYER_ENTERING_WORLD"); run()
assert(ChatFrame1:IsEventRegistered("TIME_PLAYED_MSG"), "chat frame not re-registered")
-- level up with lagging UnitLevel
now = now + 1800; fire("PLAYER_LEVEL_UP", 12); st.xp = 50; fire("PLAYER_XP_UPDATE"); run()
-- combat defers
st.combat = true; st.xp = 900; fire("PLAYER_XP_UPDATE"); run(); st.combat = false; fire("PLAYER_REGEN_ENABLED"); run()
st.level = 12; fire("PLAYER_LOGOUT")
-- second character
st.name, st.class, st.race, st.level, st.xp, st.rested = "Elowen", {"Druid","DRUID"}, {"NightElf","NightElf"}, 10, 7000, 0
playedDone = nil; fire("PLAYER_ENTERING_WORLD"); run(); fire("PLAYER_LOGOUT")
assert(#printed == 0, "addon printed to chat outside /ltrack")
assert(SLASH_LEGACYTRACKER1 == "/ltrack")
SlashCmdList.LEGACYTRACKER("")
assert(#printed == 2, "/ltrack prints one line per character"); for _, l in ipairs(printed) do io.stderr:write(l, "\n") end
local c = LegacyTrackerDB.chars["ExampleRealm-Aldric"]
assert(c.level == 12 and c.levels[12] and c.xp == 900 and c.professions.Mining.rank == 45)
-- privacy: gold and time played are off by default
assert(c.money == nil and c.timePlayed == nil, "gold or time played recorded without opt-in")
assert(LegacyTrackerDB.chars["ExampleRealm-Elowen"].money == nil)
-- opt in: both are recorded
SlashCmdList.LEGACYTRACKER("extras on"); run()
assert(#printed == 3, "extras on prints one confirmation")
local e = LegacyTrackerDB.chars["ExampleRealm-Elowen"]
fire("PLAYER_MONEY"); run()
assert(e.money == 12345 and e.timePlayed == 3600, "extras on did not record gold and time played")
assert(ChatFrame1:IsEventRegistered("TIME_PLAYED_MSG"), "chat frame not re-registered after extras on")
-- opt out: cleared everywhere
SlashCmdList.LEGACYTRACKER("extras off")
assert(e.money == nil and e.timePlayed == nil and LegacyTrackerDB.settings.extras == false, "extras off did not clear")

-- Serialize like the WoW client does.
local function ser(v, ind)
  if type(v) == "string" then return string.format("%q", v) end
  if type(v) ~= "table" then return tostring(v) end
  local keys = {}; for k in pairs(v) do keys[#keys+1] = k end
  table.sort(keys, function(a,b) return tostring(a) < tostring(b) end)
  local out = {"{\n"}
  for _, k in ipairs(keys) do
    local ks = type(k) == "string" and string.format("[%q]", k) or "[" .. k .. "]"
    out[#out+1] = ind .. "\t" .. ks .. " = " .. ser(v[k], ind .. "\t") .. ",\n"
  end
  out[#out+1] = ind .. "}"
  return table.concat(out)
end
io.write("\nLegacyTrackerDB = " .. ser(LegacyTrackerDB, "") .. "\n")
