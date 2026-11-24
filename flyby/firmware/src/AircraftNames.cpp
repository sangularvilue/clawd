// ICAO type designators (ICAO Doc 8643) for the aircraft you're most likely to
// see overhead. Anything missing falls back to the feed's own description.
#include "AircraftNames.h"

#include <string.h>

namespace {
struct TypeName {
  const char* code;
  const char* name;
};

const TypeName kTypes[] = {
    // Airbus
    {"A318", "Airbus A318"},       {"A319", "Airbus A319"},       {"A320", "Airbus A320"},
    {"A321", "Airbus A321"},       {"A19N", "Airbus A319neo"},    {"A20N", "Airbus A320neo"},
    {"A21N", "Airbus A321neo"},    {"BCS1", "Airbus A220-100"},   {"BCS3", "Airbus A220-300"},
    {"A306", "Airbus A300-600"},   {"A310", "Airbus A310"},       {"A332", "Airbus A330-200"},
    {"A333", "Airbus A330-300"},   {"A338", "Airbus A330-800"},   {"A339", "Airbus A330-900"},
    {"A342", "Airbus A340-200"},   {"A343", "Airbus A340-300"},   {"A345", "Airbus A340-500"},
    {"A346", "Airbus A340-600"},   {"A359", "Airbus A350-900"},   {"A35K", "Airbus A350-1000"},
    {"A388", "Airbus A380"},       {"A400", "Airbus A400M"},      {"A3ST", "Airbus Beluga"},
    {"A337", "Airbus BelugaXL"},
    // Boeing
    {"B712", "Boeing 717"},        {"B733", "Boeing 737-300"},    {"B734", "Boeing 737-400"},
    {"B735", "Boeing 737-500"},    {"B736", "Boeing 737-600"},    {"B737", "Boeing 737-700"},
    {"B738", "Boeing 737-800"},    {"B739", "Boeing 737-900"},    {"B37M", "Boeing 737 MAX 7"},
    {"B38M", "Boeing 737 MAX 8"},  {"B39M", "Boeing 737 MAX 9"},  {"B3XM", "Boeing 737 MAX 10"},
    {"B744", "Boeing 747-400"},    {"B748", "Boeing 747-8"},      {"B752", "Boeing 757-200"},
    {"B753", "Boeing 757-300"},    {"B762", "Boeing 767-200"},    {"B763", "Boeing 767-300"},
    {"B764", "Boeing 767-400"},    {"B772", "Boeing 777-200"},    {"B77L", "Boeing 777-200LR"},
    {"B773", "Boeing 777-300"},    {"B77W", "Boeing 777-300ER"},  {"B778", "Boeing 777-8"},
    {"B779", "Boeing 777-9"},      {"B788", "Boeing 787-8"},      {"B789", "Boeing 787-9"},
    {"B78X", "Boeing 787-10"},     {"MD11", "McDonnell MD-11"},   {"MD82", "McDonnell MD-82"},
    {"MD83", "McDonnell MD-83"},   {"MD88", "McDonnell MD-88"},   {"MD90", "McDonnell MD-90"},
    {"DC10", "McDonnell DC-10"},
    // Regional jets and turboprops
    {"E170", "Embraer E170"},      {"E75L", "Embraer E175"},      {"E75S", "Embraer E175"},
    {"E190", "Embraer E190"},      {"E195", "Embraer E195"},      {"E290", "Embraer E190-E2"},
    {"E295", "Embraer E195-E2"},   {"E135", "Embraer ERJ-135"},   {"E145", "Embraer ERJ-145"},
    {"CRJ2", "Bombardier CRJ200"}, {"CRJ7", "Bombardier CRJ700"}, {"CRJ9", "Bombardier CRJ900"},
    {"CRJX", "Bombardier CRJ1000"},{"DH8A", "Dash 8-100"},        {"DH8B", "Dash 8-200"},
    {"DH8C", "Dash 8-300"},        {"DH8D", "Dash 8-400"},        {"AT43", "ATR 42-300"},
    {"AT45", "ATR 42-500"},        {"AT46", "ATR 42-600"},        {"AT72", "ATR 72"},
    {"AT75", "ATR 72-500"},        {"AT76", "ATR 72-600"},        {"SF34", "Saab 340"},
    {"SB20", "Saab 2000"},         {"JS41", "Jetstream 41"},      {"B190", "Beech 1900"},
    {"C919", "COMAC C919"},        {"AJ27", "COMAC ARJ21"},       {"SU95", "Sukhoi Superjet"},
    // Business jets
    {"GLF4", "Gulfstream IV"},     {"GLF5", "Gulfstream V"},      {"GLF6", "Gulfstream G650"},
    {"GA5C", "Gulfstream G500"},   {"GA6C", "Gulfstream G600"},   {"GA7C", "Gulfstream G700"},
    {"G280", "Gulfstream G280"},   {"GLEX", "Global Express"},    {"GL5T", "Global 5000"},
    {"GL7T", "Global 7500"},       {"CL30", "Challenger 300"},    {"CL35", "Challenger 350"},
    {"CL60", "Challenger 600"},    {"C25A", "Citation CJ2"},      {"C25B", "Citation CJ3"},
    {"C25C", "Citation CJ4"},      {"C525", "Citation CJ1"},      {"C560", "Citation V"},
    {"C56X", "Citation Excel"},    {"C680", "Citation Sovereign"},{"C68A", "Citation Latitude"},
    {"C700", "Citation Longitude"},{"C750", "Citation X"},        {"E50P", "Phenom 100"},
    {"E55P", "Phenom 300"},        {"E545", "Praetor 500"},       {"E550", "Praetor 600"},
    {"LJ45", "Learjet 45"},        {"LJ60", "Learjet 60"},        {"LJ75", "Learjet 75"},
    {"F2TH", "Falcon 2000"},       {"FA7X", "Falcon 7X"},         {"FA8X", "Falcon 8X"},
    {"F900", "Falcon 900"},        {"PC24", "Pilatus PC-24"},     {"HDJT", "HondaJet"},
    {"SF50", "Cirrus Vision Jet"},
    // Light aircraft and turboprops
    {"C150", "Cessna 150"},        {"C152", "Cessna 152"},        {"C172", "Cessna 172"},
    {"C182", "Cessna 182"},        {"C206", "Cessna 206"},        {"C210", "Cessna 210"},
    {"C208", "Cessna Caravan"},    {"C310", "Cessna 310"},        {"P28A", "Piper Cherokee"},
    {"P28R", "Piper Arrow"},       {"PA32", "Piper Saratoga"},    {"PA34", "Piper Seneca"},
    {"PA46", "Piper Malibu"},      {"SR20", "Cirrus SR20"},       {"SR22", "Cirrus SR22"},
    {"S22T", "Cirrus SR22T"},      {"DA40", "Diamond DA40"},      {"DA42", "Diamond DA42"},
    {"DA62", "Diamond DA62"},      {"BE36", "Beech Bonanza"},     {"BE58", "Beech Baron"},
    {"BE20", "King Air 200"},      {"BE9L", "King Air 90"},       {"B350", "King Air 350"},
    {"PC12", "Pilatus PC-12"},     {"TBM7", "TBM 700"},           {"TBM9", "TBM 900"},
    {"M20P", "Mooney M20"},        {"DHC6", "Twin Otter"},        {"DHC2", "DHC-2 Beaver"},
    // Helicopters
    {"R22", "Robinson R22"},       {"R44", "Robinson R44"},       {"R66", "Robinson R66"},
    {"EC35", "Airbus H135"},       {"EC45", "Airbus H145"},       {"EC30", "Airbus H130"},
    {"EC55", "Airbus H155"},       {"EC75", "Airbus H175"},       {"AS50", "Airbus H125"},
    {"AS65", "Airbus Dauphin"},    {"A109", "AW109"},             {"A139", "AW139"},
    {"A169", "AW169"},             {"S76", "Sikorsky S-76"},      {"S92", "Sikorsky S-92"},
    {"B06", "Bell 206"},           {"B407", "Bell 407"},          {"B429", "Bell 429"},
    {"B412", "Bell 412"},          {"H60", "Black Hawk"},         {"H47", "Chinook"},
    // Military transports and tankers
    {"C17", "Boeing C-17"},        {"C130", "Lockheed C-130"},    {"C30J", "Lockheed C-130J"},
    {"C5M", "Lockheed C-5M"},      {"K35R", "Boeing KC-135"},     {"KC46", "Boeing KC-46"},
    {"P8", "Boeing P-8"},          {"E3TF", "Boeing E-3"},        {"V22", "Osprey V-22"},
};
}  // namespace

const char* lookupAircraftName(const char* typeCode) {
  if (!typeCode || !*typeCode) return nullptr;
  for (const TypeName& t : kTypes) {
    if (strcmp(t.code, typeCode) == 0) return t.name;
  }
  return nullptr;
}
