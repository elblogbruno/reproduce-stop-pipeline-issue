set(INCLUDE_DIRS
    .
)

set(REQUIRES
    depthai-spi-api
    arduino
    json
)

set(SOURCES
    "main.cpp"
    "ESP32_Utils_OTA.hpp"
    "ESP32_Utils.hpp"
    "name_utils.hpp"
)


idf_component_register(SRCS ${SOURCES} INCLUDE_DIRS ${INCLUDE_DIRS} REQUIRES ${REQUIRES} PRIV_REQUIRES ${PRIV_REQUIRES})