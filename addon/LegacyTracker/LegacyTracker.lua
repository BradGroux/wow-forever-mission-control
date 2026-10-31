-- LegacyTracker: silent per-character level, XP, rested and profession recorder. No UI, no chat output except /ltrack.
-- Data: LegacyTrackerDB.chars["Realm-Name"] (account-wide SavedVariables).
local ADDON = ...
local DB_VERSION = 1

local f = CreateFrame("Frame")
local pending, dirty, playedRequested = false, false, false
local key -- "Realm-Name" for the logged-in character

local function fn(x) return type(x) == "function" end

-- Values can be "secret" in the modern client WoW Forever runs on (mainly in combat); never touch them.
local function plain(v)
  if fn(issecretvalue) and issecretvalue(v) then return nil end
  return v
end

local function inCombat()
  return (fn(InCombatLockdown) and InCombatLockdown())
      or (fn(UnitAffectingCombat) and UnitAffectingCombat("player"))
end

local function charKey()
  local name = UnitName("player")
  if not name or name == "" or name == UNKNOWNOBJECT or name == "Unknown" then return nil end
  local realm = fn(GetNormalizedRealmName) and GetNormalizedRealmName() or nil
  if not realm or realm == "" then realm = GetRealmName() end
  if not realm or realm == "" then return nil end
  return realm .. "-" .. name, name, realm
end

local function getDB()
  LegacyTrackerDB = LegacyTrackerDB or {}
  local db = LegacyTrackerDB
  db.version = DB_VERSION
  db.chars = db.chars or {}
  return db
end

local function professions()
  local out = {}
  if fn(GetProfessions) and fn(GetProfessionInfo) then
    local idx = { GetProfessions() }
    for i = 1, 5 do
      local p = idx[i]
      if p then
        local name, _, rank, maxRank = GetProfessionInfo(p)
        if name then out[name] = { rank = rank, max = maxRank } end
      end
    end
  elseif fn(GetNumSkillLines) and fn(GetSkillLineInfo) then
    for i = 1, GetNumSkillLines() do
      local name, isHeader, _, rank, _, _, maxRank = GetSkillLineInfo(i)
      if name and not isHeader and maxRank and maxRank > 1 then
        out[name] = { rank = rank, max = maxRank }
      end
    end
  end
  return out
end

local function snapshot(skills)
  local k, name, realm = charKey()
  if not k then return end
  key = k
  local db = getDB()
  local c = db.chars[k] or { levels = {}, firstSeen = time() }
  db.chars[k] = c
  c.levels = c.levels or {}

  c.name, c.realm = name, realm
  local _, classFile = UnitClass("player")
  local _, raceFile = UnitRace("player")
  c.class, c.race = classFile, raceFile
  c.className = (UnitClass("player"))
  c.raceName = (UnitRace("player"))
  c.faction = fn(UnitFactionGroup) and (UnitFactionGroup("player")) or nil

  local lvl = plain(UnitLevel("player"))
  if lvl and lvl > (c.level or 0) or not c.level then c.level = lvl end
  local xp, xpMax = plain(UnitXP("player")), plain(UnitXPMax("player"))
  if xp and xpMax then
    c.xp, c.xpMax = xp, xpMax
    local rested = (fn(GetXPExhaustion) and plain(GetXPExhaustion())) or 0
    c.rested = rested
    if xpMax > 0 then
      c.restedPctOfLevel = math.floor(rested / xpMax * 1000 + 0.5) / 10
      c.pctToNext = math.floor(xp / xpMax * 1000 + 0.5) / 10
    else
      c.restedPctOfLevel, c.pctToNext = 0, 0
    end
  end
  if fn(GetRestState) then
    local id, stateName, mult = GetRestState()
    c.restState = { id = id, name = stateName, mult = mult }
  end
  if fn(IsResting) then c.resting = IsResting() and true or false end
  c.zone = fn(GetRealZoneText) and GetRealZoneText() or nil
  c.subzone = fn(GetSubZoneText) and GetSubZoneText() or nil
  if fn(GetMoney) then c.money = plain(GetMoney()) or c.money end
  if skills or not c.professions then c.professions = professions() end
  c.lastSeen = time()
end

local function flush()
  pending = false
  if inCombat() then dirty = true return end
  dirty = false
  pcall(snapshot, true)
end

-- Coalesce bursts of events into one snapshot.
local function schedule(delay)
  if pending then return end
  pending = true
  if C_Timer and fn(C_Timer.After) then C_Timer.After(delay or 2, flush) else flush() end
end

-- /played without chat output: mute TIME_PLAYED_MSG on chat frames for one request.
local muted = {}
local function unmute()
  for frame in pairs(muted) do frame:RegisterEvent("TIME_PLAYED_MSG") end
  wipe(muted)
end
local function requestPlayed()
  if playedRequested or not fn(RequestTimePlayed) or inCombat() then return end
  if not (C_Timer and fn(C_Timer.After)) then return end
  playedRequested = true
  for i = 1, (NUM_CHAT_WINDOWS or 10) do
    local cf = _G["ChatFrame" .. i]
    if cf and cf.IsEventRegistered and cf:IsEventRegistered("TIME_PLAYED_MSG") then
      cf:UnregisterEvent("TIME_PLAYED_MSG")
      muted[cf] = true
    end
  end
  f:RegisterEvent("TIME_PLAYED_MSG")
  RequestTimePlayed()
  C_Timer.After(10, unmute) -- safety net if the reply never arrives
end

f:SetScript("OnEvent", function(_, event, ...)
  if event == "PLAYER_LOGOUT" then
    pcall(snapshot, false)
  elseif event == "PLAYER_LEVEL_UP" then
    local newLevel = ...
    pcall(snapshot, false)
    local c = key and LegacyTrackerDB and LegacyTrackerDB.chars[key]
    if c and newLevel then
      c.level = newLevel -- UnitLevel can lag behind the event
      c.levels[newLevel] = time()
    end
    schedule(3)
  elseif event == "TIME_PLAYED_MSG" then
    local total, thisLevel = ...
    f:UnregisterEvent("TIME_PLAYED_MSG")
    local c = key and LegacyTrackerDB and LegacyTrackerDB.chars[key]
    if c then c.timePlayed, c.timePlayedLevel = total, thisLevel end
    if C_Timer and fn(C_Timer.After) then C_Timer.After(0, unmute) else unmute() end
  elseif event == "PLAYER_REGEN_ENABLED" then
    if dirty then schedule(1) end
  elseif event == "PLAYER_ENTERING_WORLD" then
    schedule(2)
    if C_Timer and fn(C_Timer.After) then C_Timer.After(8, requestPlayed) end
  elseif event == "SKILL_LINES_CHANGED" then
    schedule(2)
  else
    schedule(2)
  end
end)

for _, e in ipairs({
  "PLAYER_ENTERING_WORLD", "PLAYER_LEVEL_UP", "PLAYER_XP_UPDATE", "UPDATE_EXHAUSTION",
  "PLAYER_UPDATE_RESTING", "ZONE_CHANGED_NEW_AREA", "PLAYER_MONEY", "SKILL_LINES_CHANGED",
  "PLAYER_LOGOUT", "PLAYER_REGEN_ENABLED",
}) do
  pcall(f.RegisterEvent, f, e)
end

SLASH_LEGACYTRACKER1 = "/ltrack"
SlashCmdList.LEGACYTRACKER = function()
  if not inCombat() then pcall(snapshot, true) end
  local chars = LegacyTrackerDB and LegacyTrackerDB.chars or {}
  local keys = {}
  for k in pairs(chars) do keys[#keys + 1] = k end
  table.sort(keys)
  if #keys == 0 then print("|cff33ff99LegacyTracker|r: no characters recorded yet.") return end
  for _, k in ipairs(keys) do
    local c = chars[k]
    local bubbles = (c.xpMax and c.xpMax > 0) and (c.rested or 0) / (c.xpMax / 20) or 0
    print(string.format("|cff33ff99%s|r %s L%d  %.1f%% to next  rested %.1f bubbles%s",
      ADDON, k, c.level or 0, c.pctToNext or 0, bubbles, c.resting and "  (resting)" or ""))
  end
end
