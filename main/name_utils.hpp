/* Returns a semi-unique id for the device. The id is based
*  on part of a MAC address or chip ID so it won't be 
*  globally unique. */
uint16_t GetDeviceId()
{
    #if defined(ARDUINO_ARCH_ESP32)
    return ESP.getEfuseMac();
    #else
    return ESP.getChipId();
    #endif
}
 
/* Append a semi-unique id to the name template */
String MakeMine(const char *NameTemplate)
{
  uint16_t uChipId = GetDeviceId();
  String Result = String(NameTemplate) + String(uChipId, HEX);
  return Result;
}