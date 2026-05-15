cmake_minimum_required(VERSION 3.10)

project(openFPGALoader VERSION "1.1.1" LANGUAGES CXX)

#if(CMAKE_SYSTEM_NAME STREQUAL "Windows" AND NOT CMAKE_HOST_SYSTEM_NAME STREQUAL "Windows")
#	set(WINDOWS_CROSSCOMPILE ON)
#else()
#	set(WINDOWS_CROSSCOMPILE OFF)
#endif()

####################################################################################################
# Generic Options
####################################################################################################

option(ENABLE_OPTIM       "Enable build with -O3 optimization level"             ON)
option(BUILD_STATIC       "Whether or not to build with static libraries"        OFF)
option(USE_PKGCONFIG      "Use pkgconfig to find libraries"                      ON)
option(LINK_CMAKE_THREADS "Use CMake find_package to link the threading library" OFF)
option(WINDOWS_CROSSCOMPILE "Enable cross-compile on Windows"                    OFF)
option(WINDOWS_STATIC_ZLIB "Link zlib statically for Windows builds"             ON)

if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
	set(ENABLE_UDEV OFF)
else()
	option(ENABLE_UDEV "use udev to search JTAG adapter from /dev/xx" ON)
endif()

option(ENABLE_USB_SCAN "Enable USB Scan option" ON)

####################################################################################################
# CABLES Options
####################################################################################################

# Enable all cables by default
option(ENABLE_CABLE_ALL        "Enable all cables"                            ON)

option(ENABLE_ANLOGIC_CABLE    "enable Anlogic cable (requires libUSB)"       ${ENABLE_CABLE_ALL})
option(ENABLE_CH347            "enable CH347 cable (requires libUSB)"         ${ENABLE_CABLE_ALL})
# CMSIS-DAP requires hidapi which is complex to cross-compile, disable by default for cross-compilation
if (NOT WINDOWS_CROSSCOMPILE)
	option(ENABLE_CMSISDAP     "enable cmsis DAP interface (requires hidapi)" ${ENABLE_CABLE_ALL})
else()
	option(ENABLE_CMSISDAP     "enable cmsis DAP interface (requires hidapi)" OFF)
endif()
option(ENABLE_DIRTYJTAG        "enable dirtyJtag cable (requires libUSB)"     ${ENABLE_CABLE_ALL})
option(ENABLE_ESP_USB          "enable ESP32S3 cable (requires libUSB)"       ${ENABLE_CABLE_ALL})
option(ENABLE_JLINK            "enable JLink cable (requires libUSB)"         ${ENABLE_CABLE_ALL})
option(ENABLE_DFU              "enable DFU support (requires libUSB)"         ${ENABLE_CABLE_ALL})
option(ENABLE_FTDI_BASED_CABLE "enable cables based on FTDI (requires libFTDI)" ${ENABLE_CABLE_ALL})
option(ENABLE_GOWIN_GWU2X      "enable Gowin GWU2X interface"                 ${ENABLE_CABLE_ALL})
option(ENABLE_JETSONNANOGPIO   "enable Jetson Nano GPIO bitbang driver"       OFF)
option(ENABLE_SVF_JTAG         "enable SVF support"                           ${ENABLE_CABLE_ALL})
option(ENABLE_USB_BLASTERI     "enable Altera USB Blaster I support"          ${ENABLE_CABLE_ALL})
option(ENABLE_USB_BLASTERII    "enable Altera USB Blaster II support"         ${ENABLE_CABLE_ALL})

set(BLASTERII_PATH           "" CACHE STRING "usbBlasterII firmware directory")
set(ISE_PATH "/opt/Xilinx/14.7" CACHE STRING "ise root directory (default: /opt/Xilinx/14.7)")
set(VIVADO_PATH              "" CACHE STRING "Vivado root directory (something like /opt/Xilinx/Vivado/VERSION)")

# Libgpiod is only available on Linux OS.
if (${CMAKE_SYSTEM_NAME} MATCHES "Linux")
	option(ENABLE_LIBGPIOD "enable libgpiod bitbang driver (requires libgpiod)" ${ENABLE_CABLE_ALL})
else()
	set(ENABLE_LIBGPIOD OFF)
endif()

option(ENABLE_XILINX_PLATFORM_CABLE_USB "enable Xilinx Platform Cable USB (XPCU) support" ${ENABLE_CABLE_ALL})

# XVC and RemoteBitbang are not available on Windows OS.
if (NOT ${CMAKE_SYSTEM_NAME} MATCHES "Windows")
	option(ENABLE_REMOTEBITBANG               "enable remote bitbang driver"              ${ENABLE_CABLE_ALL})
	option(ENABLE_XILINX_VIRTUAL_CABLE_CLIENT "enable Xilinx Virtual Cable (XVC) client support" ${ENABLE_CABLE_ALL})
	option(ENABLE_XILINX_VIRTUAL_CABLE_SERVER "enable Xilinx Virtual Cable (XVC) server support" ${ENABLE_CABLE_ALL})
else()
	set(ENABLE_REMOTEBITBANG               OFF)
	set(ENABLE_XILINX_VIRTUAL_CABLE_CLIENT OFF)
	set(ENABLE_XILINX_VIRTUAL_CABLE_SERVER OFF)
endif()

####################################################################################################
# VENDORS Options
####################################################################################################

# Enable all vendors by default
option(ENABLE_VENDORS_ALL         "Enable all vendors support"                             ON)

option(ENABLE_ALTERA_SUPPORT      "enable Altera FPGAs Support"                            ${ENABLE_VENDORS_ALL})
option(ENABLE_ANLOGIC_SUPPORT     "enable Anlogic FPGAs Support"                           ${ENABLE_VENDORS_ALL})
option(ENABLE_COLOGNECHIP_SUPPORT "enable CologneChip FPGAs Support (requires libftdi)"    ${ENABLE_VENDORS_ALL})
option(ENABLE_EFINIX_SUPPORT      "enable Efinix FPGAs Support (requires libftdi)"         ${ENABLE_VENDORS_ALL})
option(ENABLE_GOWIN_SUPPORT       "enable Gowin FPGAs Support"                             ${ENABLE_VENDORS_ALL})
option(ENABLE_ICE40_SUPPORT       "enable Ice40 FPGAs Support (requires libftdi)"          ${ENABLE_VENDORS_ALL})
option(ENABLE_LATTICE_SUPPORT     "enable Lattice FPGAs Support"                           ${ENABLE_VENDORS_ALL})
option(ENABLE_LATTICESSPI_SUPPORT "enable Lattice FPGAs Support (SSPI / requires libftdi)" ${ENABLE_VENDORS_ALL})
option(ENABLE_XILINX_SUPPORT      "enable Xilinx FPGAs Support"                            ${ENABLE_VENDORS_ALL})

####################################################################################################
# Variables
####################################################################################################

# set dependencies
set(USE_FX2_LL    OFF)
set(USE_LIBFTDI   OFF)
set(USE_LIBUSB    OFF)
set(USE_LIBUSB_LL OFF)
set(OPENFPGALOADER_COMPILE_DEFINITIONS)

macro(openfpgaloader_add_optional_sources option)
	if (${option})
		list(APPEND OPENFPGALOADER_SOURCE ${ARGN})
	endif()
endmacro()

macro(openfpgaloader_add_optional_headers option)
	if (${option})
		list(APPEND OPENFPGALOADER_HEADERS ${ARGN})
	endif()
endmacro()

# USB BlasterII and Xilinx Platform Cable USB require the FX2 driver
if (ENABLE_XILINX_PLATFORM_CABLE_USB OR ENABLE_USB_BLASTERII)
	set(USE_FX2_LL ON)
endif()

# Only add libftdi as a dependency when a cable needs this library.
if (ENABLE_FTDI_BASED_CABLE OR ENABLE_USB_BLASTERI OR ENABLE_XILINX_VIRTUAL_CABLE_SERVER)
	set(USE_LIBFTDI ON)
else()
	message("disabled all cables based on FTDI devices")
endif(ENABLE_FTDI_BASED_CABLE OR ENABLE_USB_BLASTERI OR ENABLE_XILINX_VIRTUAL_CABLE_SERVER)

# Only add libusb as a dependency when a cable needs this library
if (ENABLE_DFU OR ENABLE_ANLOGIC_CABLE OR ENABLE_CH347 OR ENABLE_DIRTYJTAG
		OR ENABLE_ESP_USB OR ENABLE_JLINK OR ENABLE_GOWIN_GWU2X OR USE_FX2_LL OR ENABLE_USB_SCAN)
	set(USE_LIBUSB ON)
endif()

if (ENABLE_USB_SCAN OR ENABLE_GOWIN_GWU2X)
	set(USE_LIBUSB_LL ON)
endif()

####################################################################################################
# Cross-compilation support
####################################################################################################

# Detect cross-compilation for Windows from Linux/macOS
if(WINDOWS_CROSSCOMPILE)
	set(CROSS_COMPILING_WINDOWS TRUE)
	message(STATUS "Cross-compiling for Windows from ${CMAKE_HOST_SYSTEM_NAME}")

	# Option to automatically download and build cross-compile dependencies
	option(CROSS_COMPILE_DEPS "Download and build Windows dependencies for cross-compilation" ON)

	if(CROSS_COMPILE_DEPS)
		# Include the cross-compilation module
		list(INSERT CMAKE_MODULE_PATH 0 ${PROJECT_SOURCE_DIR}/cmake/Modules)
		include(CrossCompileWindows)

		# Setup the dependencies (downloads libusb, builds libftdi)
		setup_windows_cross_compile_deps()

		# Update pkg-config path for the dependencies
		set(ENV{PKG_CONFIG_PATH} "${CROSS_DEPS_INSTALL_DIR}/lib/pkgconfig:$ENV{PKG_CONFIG_PATH}")

		# Add the cross-compiled dependencies to the search path
		list(APPEND CMAKE_PREFIX_PATH ${CROSS_DEPS_INSTALL_DIR})
		include_directories(${CROSS_DEPS_INSTALL_DIR}/include)
		link_directories(${CROSS_DEPS_INSTALL_DIR}/lib)
	endif()
else()
	set(CROSS_COMPILING_WINDOWS FALSE)
endif()

####################################################################################################
# Build options
####################################################################################################

## specify the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_FLAGS_DEBUG "-g -Wall -Wextra ${CMAKE_CXX_FLAGS_DEBUG}")
if(ENABLE_OPTIM AND NOT(CMAKE_BUILD_TYPE STREQUAL "Debug"))
	set(CMAKE_CXX_FLAGS "-O3 ${CMAKE_CXX_FLAGS}")
endif()

if (BUILD_STATIC)
	set(CMAKE_EXE_LINKER_FLAGS "-static-libstdc++ -static ${CMAKE_EXE_LINKER_FLAGS}")
	set(BUILD_SHARED_LIBS OFF)
endif()

include(GNUInstallDirs)

####################################################################################################
# Dependencies check/search
####################################################################################################

if (USE_LIBFTDI)
	# Try to find the LibFTDI1 with cmake
	find_package(LibFTDI1 QUIET)
endif()

if (USE_PKGCONFIG)
	find_package(PkgConfig REQUIRED)

	# Backward compat when the libftdi is not found
	# by using cmake
	if (USE_LIBFTDI)
		if (NOT LIBFTDI_FOUND)
			pkg_check_modules(LIBFTDI REQUIRED libftdi1)
			string(REPLACE "." ";" VERSION_LIST ${LIBFTDI_VERSION})
			list(GET VERSION_LIST 0 LIBFTDI_VERSION_MAJOR)
			list(GET VERSION_LIST 1 LIBFTDI_VERSION_MINOR)
			string(REGEX REPLACE "[^0-9].*" "" LIBFTDI_VERSION_MINOR "${LIBFTDI_VERSION_MINOR}")
		endif()
	else()
		set(LIBFTDI_LIBRARY_DIRS "")
		set(LIBFTDI_INCLUDE_DIRS "")
		set(LIBFTDI_LIBRARIES    "")
	endif(USE_LIBFTDI)

	if (USE_LIBUSB)
		pkg_check_modules(LIBUSB REQUIRED libusb-1.0)
	else()
		set(LIBUSB_LIBRARY_DIRS "")
		set(LIBUSB_INCLUDE_DIRS "")
		set(LIBUSB_LIBRARIES    "")
	endif(USE_LIBUSB)

	if(ENABLE_CMSISDAP)
		pkg_check_modules(HIDAPI hidapi-libusb)
		# if libusb not found try with hidraw
		if (NOT HIDAPI_FOUND)
			pkg_check_modules(HIDAPI hidapi-hidraw)
		endif()
		if (NOT HIDAPI_FOUND)
			pkg_check_modules(HIDAPI hidapi)
		endif()
	endif()

	# zlib support (gzip)
	if(WINDOWS_CROSSCOMPILE)
		if (WINDOWS_STATIC_ZLIB)
			set(ZLIB_USE_STATIC_LIBS ON)
		endif()

		# Use CMake zlib finder for Windows builds to avoid host pkg-config contamination
		# during cross-compilation and to allow static linking selection.
		find_package(ZLIB QUIET)
		if (NOT ZLIB_FOUND)
			if (WINDOWS_CROSSCOMPILE)
				message(FATAL_ERROR
					"zlib for Windows target not found. Install MinGW zlib development files "
					"(for example: libz-mingw-w64-dev on Debian/Ubuntu or mingw64-zlib on Fedora).")
			else()
				message(FATAL_ERROR
					"zlib for Windows build not found. Install zlib development files for your "
					"Windows toolchain.")
			endif()
		endif()

		if (WINDOWS_STATIC_ZLIB AND ZLIB_LIBRARIES MATCHES "\\.dll\\.a$")
			message(FATAL_ERROR
				"Static zlib requested (WINDOWS_STATIC_ZLIB=ON), but CMake selected "
				"'${ZLIB_LIBRARIES}'. Install static zlib (for example mingw64-zlib-static) "
				"or set -DWINDOWS_STATIC_ZLIB=OFF.")
		endif()
	else()
		pkg_check_modules(ZLIB zlib)
		if (NOT ZLIB_FOUND)
			# try zlib-ng
			pkg_check_modules(ZLIB zlib-ng)
			if (ZLIB_FOUND)
				list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS HAS_ZLIBNG)
			else()
				message(FATAL_ERROR "Could find ZLIB")
			endif()
		endif(NOT ZLIB_FOUND)
	endif()

	if (ENABLE_UDEV)
		pkg_check_modules(LIBUDEV libudev)
		if (LIBUDEV_FOUND)
			list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS USE_UDEV)
		else()
			message("libudev not found, disabling udev support and -D parameter")
			set(ENABLE_UDEV OFF)
		endif()
	endif()

	if (ENABLE_LIBGPIOD)
		pkg_check_modules(LIBGPIOD libgpiod)
		if (NOT LIBGPIOD_FOUND)
			message("libgpiod not found, disabling gpiod support")
			set(ENABLE_LIBGPIOD OFF)
		endif()
	endif()
endif()

####################################################################################################
# FILES
####################################################################################################

# ===========================
# Core Classes
# ===========================
set(OPENFPGALOADER_SOURCE
	src/common.cpp
	src/configBitstreamParser.cpp
	src/device.cpp
	src/display.cpp
	src/main.cpp
	src/progressBar.cpp
)

set(OPENFPGALOADER_HEADERS
	src/board.hpp
	src/cable.hpp
	src/common.hpp
	src/configBitstreamParser.hpp
	src/cxxopts.hpp
	src/device.hpp
	src/display.hpp
	src/part.hpp
	src/progressBar.hpp
)

# ===========================
# Parsers classes
# ===========================
list(APPEND OPENFPGALOADER_SOURCE  src/rawParser.cpp)
list(APPEND OPENFPGALOADER_HEADERS src/rawParser.hpp)

if (${ENABLE_LATTICE_SUPPORT} OR ${ENABLE_XILINX_SUPPORT})
	list(APPEND OPENFPGALOADER_SOURCE
		src/jedParser.cpp
		src/mcsParser.cpp
	)

	list(APPEND OPENFPGALOADER_HEADERS
		src/jedParser.hpp
		src/mcsParser.hpp
	)
endif()

# ===========================
# Flash and JTAG core support
# ===========================
list(APPEND OPENFPGALOADER_SOURCE
	src/bpiFlash.cpp
	src/spiFlash.cpp
	src/flashInterface.cpp
	src/jtag.cpp
)

list(APPEND OPENFPGALOADER_HEADERS
	src/bpiFlash.hpp
	src/jtag.hpp
	src/jtagInterface.hpp
	src/spiFlash.hpp
	src/spiFlashdb.hpp
	src/flashInterface.hpp
)

# FTDI Based cables
if (${USE_LIBFTDI})
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS USE_LIBFTDI)

	list(APPEND OPENFPGALOADER_SOURCE
		src/ch552_jtag.cpp
		src/ftdiJtagBitbang.cpp
		src/ftdiJtagMPSSE.cpp
		src/ftdipp_mpsse.cpp
		src/ftdispi.cpp
	)

	list(APPEND OPENFPGALOADER_HEADERS
		src/ch552_jtag.hpp
		src/ftdiJtagBitbang.hpp
		src/ftdiJtagMPSSE.hpp
		src/ftdipp_mpsse.hpp
		src/ftdispi.hpp
	)

	# CologneChip Drivers / Files parsers.
	if (ENABLE_COLOGNECHIP_SUPPORT)
		list(APPEND OPENFPGALOADER_SOURCE
			src/colognechip.cpp
			src/colognechipCfgParser.cpp
		)

		list(APPEND OPENFPGALOADER_HEADERS
			src/colognechip.hpp
			src/colognechipCfgParser.hpp
		)
		list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_COLOGNECHIP_SUPPORT=1)
		message("CologneChip support enabled")
	else()
		message("CologneChip support disabled")
	endif(ENABLE_COLOGNECHIP_SUPPORT)

	# Efinix Drivers / Files parsers.
	if (ENABLE_EFINIX_SUPPORT)
		list(APPEND OPENFPGALOADER_SOURCE
			src/efinix.cpp
			src/efinixHexParser.cpp
		)

		list(APPEND OPENFPGALOADER_HEADERS
			src/efinix.hpp
			src/efinixHexParser.hpp
		)
		list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_EFINIX_SUPPORT=1)
		message("Efinix support enabled")
	else()
		message("Efinix support disabled")
	endif(ENABLE_EFINIX_SUPPORT)

	# ICE40 Driver.
	if (ENABLE_ICE40_SUPPORT)
		list(APPEND OPENFPGALOADER_SOURCE  src/ice40.cpp)
		list(APPEND OPENFPGALOADER_HEADERS src/ice40.hpp)
		list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_ICE40_SUPPORT=1)
		message("ICE40 support enabled")
	else()
		message("ICE40 support disabled")
	endif(ENABLE_ICE40_SUPPORT)

	# Lattice SSPI Driver.
	if (ENABLE_LATTICESSPI_SUPPORT)
		list(APPEND OPENFPGALOADER_SOURCE  src/latticeSSPI.cpp)
		list(APPEND OPENFPGALOADER_HEADERS src/latticeSSPI.hpp)
		list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_LATTICESSPI_SUPPORT=1)
		message("Lattice SSPI support enabled")
	else()
		message("Lattice SSPI support disabled")
	endif(ENABLE_LATTICESSPI_SUPPORT)
endif()

# Altera Drivers / Files parsers.
if (ENABLE_ALTERA_SUPPORT)
	list(APPEND OPENFPGALOADER_SOURCE
		src/altera.cpp
		src/pofParser.cpp
	)

	list(APPEND OPENFPGALOADER_HEADERS
		src/altera.hpp
		src/pofParser.hpp
	)
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_ALTERA_SUPPORT=1)
	message("Altera support enabled")
else()
	message("Altera support disabled")
endif(ENABLE_ALTERA_SUPPORT)

# Anlogic Drivers / Files parsers.
if (ENABLE_ANLOGIC_SUPPORT)
	list(APPEND OPENFPGALOADER_SOURCE
		src/anlogic.cpp
		src/anlogicBitParser.cpp
	)

	list(APPEND OPENFPGALOADER_HEADERS
		src/anlogic.hpp
		src/anlogicBitParser.hpp
	)
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_ANLOGIC_SUPPORT=1)
	message("Anlogic support enabled")
else()
	message("Anlogic support disabled")
endif(ENABLE_ANLOGIC_SUPPORT)

# Gowin Drivers / Files parsers.
if (ENABLE_GOWIN_SUPPORT)
	list(APPEND OPENFPGALOADER_SOURCE
		src/gowin.cpp
		src/fsparser.cpp
	)

	list(APPEND OPENFPGALOADER_HEADERS
		src/gowin.hpp
		src/fsparser.hpp
	)
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_GOWIN_SUPPORT=1)
	message("Gowin support enabled")
else()
	message("Gowin support disabled")
endif(ENABLE_GOWIN_SUPPORT)

# Xilinx Drivers / Files parsers.
if (ENABLE_XILINX_SUPPORT)
	list(APPEND OPENFPGALOADER_SOURCE
		src/bitparser.cpp
		src/xilinx.cpp
		src/xilinxMapParser.cpp
	)

	list(APPEND OPENFPGALOADER_HEADERS
		src/bitparser.hpp
		src/xilinx.hpp
		src/xilinxMapParser.hpp
	)
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_XILINX_SUPPORT=1)
	message("Xilinx support enabled")
else()
	message("Xilinx support disabled")
endif(ENABLE_XILINX_SUPPORT)

# Lattice Drivers / Files parsers.
if (ENABLE_LATTICE_SUPPORT)
	list(APPEND OPENFPGALOADER_SOURCE
		src/lattice.cpp
		src/feaparser.cpp
		src/latticeBitParser.cpp
	)

	list(APPEND OPENFPGALOADER_HEADERS
		src/lattice.hpp
		src/feaparser.hpp
		src/latticeBitParser.hpp
	)
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_LATTICE_SUPPORT=1)
	message("Lattice support enabled")
else()
	message("Lattice support disabled")
endif(ENABLE_LATTICE_SUPPORT)

# Cables select

# DFU
openfpgaloader_add_optional_sources(ENABLE_DFU
	src/dfu.cpp
	src/dfuFileParser.cpp
)
openfpgaloader_add_optional_headers(ENABLE_DFU
	src/dfu.hpp
	src/dfuFileParser.hpp
)

# Anlogic Cable
openfpgaloader_add_optional_sources(ENABLE_ANLOGIC_CABLE src/anlogicCable.cpp)
openfpgaloader_add_optional_headers(ENABLE_ANLOGIC_CABLE src/anlogicCable.hpp)

# CH347
openfpgaloader_add_optional_sources(ENABLE_CH347 src/ch347jtag.cpp)
openfpgaloader_add_optional_headers(ENABLE_CH347 src/ch347jtag.hpp)

# dirtyJtag
openfpgaloader_add_optional_sources(ENABLE_DIRTYJTAG src/dirtyJtag.cpp)
openfpgaloader_add_optional_headers(ENABLE_DIRTYJTAG src/dirtyJtag.hpp)

# ESP32S3
openfpgaloader_add_optional_sources(ENABLE_ESP_USB src/esp_usb_jtag.cpp)
openfpgaloader_add_optional_headers(ENABLE_ESP_USB src/esp_usb_jtag.hpp)

# Gowin GWU2X JTAG interface
openfpgaloader_add_optional_sources(ENABLE_GOWIN_GWU2X src/gwu2x_jtag.cpp)
openfpgaloader_add_optional_headers(ENABLE_GOWIN_GWU2X src/gwu2x_jtag.hpp)

# Jetson Nano (libGPIO based)
openfpgaloader_add_optional_sources(ENABLE_JETSONNANOGPIO src/jetsonNanoJtagBitbang.cpp)
openfpgaloader_add_optional_headers(ENABLE_JETSONNANOGPIO src/jetsonNanoJtagBitbang.hpp)

# JLINK
openfpgaloader_add_optional_sources(ENABLE_JLINK src/jlink.cpp)
openfpgaloader_add_optional_headers(ENABLE_JLINK src/jlink.hpp)

# libGPIOD support
openfpgaloader_add_optional_sources(ENABLE_LIBGPIOD src/libgpiodJtagBitbang.cpp)
openfpgaloader_add_optional_headers(ENABLE_LIBGPIOD src/libgpiodJtagBitbang.hpp)

# RemoteBitbang
openfpgaloader_add_optional_sources(ENABLE_REMOTEBITBANG src/remoteBitbang_client.cpp)
openfpgaloader_add_optional_headers(ENABLE_REMOTEBITBANG src/remoteBitbang_client.hpp)

# SVF JTAG file type support
openfpgaloader_add_optional_sources(ENABLE_SVF_JTAG src/svf_jtag.cpp)
openfpgaloader_add_optional_headers(ENABLE_SVF_JTAG src/svf_jtag.hpp)
if (ENABLE_SVF_JTAG)
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_SVF_JTAG)
endif()

# Xilinx Platform Cable USB
openfpgaloader_add_optional_sources(ENABLE_XILINX_PLATFORM_CABLE_USB src/xilinxPlatformCableUSB.cpp)
openfpgaloader_add_optional_headers(ENABLE_XILINX_PLATFORM_CABLE_USB src/xilinxPlatformCableUSB.hpp)

# Xilinx Virtual Cable
openfpgaloader_add_optional_sources(ENABLE_XILINX_VIRTUAL_CABLE_CLIENT src/xvc_client.cpp)
openfpgaloader_add_optional_headers(ENABLE_XILINX_VIRTUAL_CABLE_CLIENT src/xvc_client.hpp)
openfpgaloader_add_optional_sources(ENABLE_XILINX_VIRTUAL_CABLE_SERVER src/xvc_server.cpp)
openfpgaloader_add_optional_headers(ENABLE_XILINX_VIRTUAL_CABLE_SERVER src/xvc_server.hpp)

# Altera USB Blaster (I & II).
if (ENABLE_USB_BLASTERI OR ENABLE_USB_BLASTERII)
	list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_USBBLASTER)

	if (ENABLE_USB_BLASTERI)
		list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS ENABLE_USB_BLASTERI)
	endif()

	if (ENABLE_USB_BLASTERII)
		list(APPEND OPENFPGALOADER_COMPILE_DEFINITIONS
			BLASTERII_DIR="${BLASTERII_PATH}"
			ENABLE_USB_BLASTERII
		)
	endif (ENABLE_USB_BLASTERII)

	list(APPEND OPENFPGALOADER_SOURCE  src/usbBlaster.cpp)
	list(APPEND OPENFPGALOADER_HEADERS src/usbBlaster.hpp)
endif(ENABLE_USB_BLASTERI OR ENABLE_USB_BLASTERII)

openfpgaloader_add_optional_sources(USE_LIBUSB_LL src/libusb_ll.cpp)
openfpgaloader_add_optional_headers(USE_LIBUSB_LL src/libusb_ll.hpp)

openfpgaloader_add_optional_sources(USE_FX2_LL src/fx2_ll.cpp src/ihexParser.cpp)
openfpgaloader_add_optional_headers(USE_FX2_LL src/fx2_ll.hpp src/ihexParser.hpp)

add_executable(openFPGALoader
	${OPENFPGALOADER_SOURCE}
	${OPENFPGALOADER_HEADERS}
)

target_compile_definitions(openFPGALoader PRIVATE
	VERSION="v${PROJECT_VERSION}"
	DATA_DIR="${CMAKE_INSTALL_FULL_DATAROOTDIR}"
	ISE_DIR="${ISE_PATH}"
	VIVADO_DIR="${VIVADO_PATH}"
	${OPENFPGALOADER_COMPILE_DEFINITIONS}
)

target_include_directories(openFPGALoader PRIVATE
	${LIBUSB_INCLUDE_DIRS}
	${LIBFTDI_INCLUDE_DIRS}
)

target_link_directories(openFPGALoader PRIVATE
	${LIBUSB_LIBRARY_DIRS}
	${LIBFTDI_LIBRARY_DIRS}
)

target_link_libraries(openFPGALoader PRIVATE
	${LIBUSB_LIBRARIES}
	${LIBFTDI_LIBRARIES}
)

if (${CMAKE_SYSTEM_NAME} MATCHES "Windows")
	# winsock provides ntohs
	target_link_libraries(openFPGALoader PRIVATE ws2_32)

	target_sources(openFPGALoader PRIVATE src/pathHelper.cpp)
	list(APPEND OPENFPGALOADER_HEADERS src/pathHelper.hpp)
endif()

# libusb_attach_kernel_driver is only available on Linux.
if (${CMAKE_SYSTEM_NAME} MATCHES "Linux")
	target_compile_definitions(openFPGALoader PRIVATE ATTACH_KERNEL)
endif()

if (ENABLE_UDEV)
	target_include_directories(openFPGALoader PRIVATE ${LIBUDEV_INCLUDE_DIRS})
	target_link_libraries(openFPGALoader PRIVATE ${LIBUDEV_LIBRARIES})
endif()

if (BUILD_STATIC)
	set_target_properties(openFPGALoader PROPERTIES LINK_SEARCH_END_STATIC 1)
endif()

# Anlogic Cable
if (ENABLE_ANLOGIC_CABLE)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_ANLOGIC_CABLE=1)
	message("Anlogic Cable support enabled")
else()
	message("Anlogic Cable support disabled")
endif()

# CH347
if (ENABLE_CH347)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_CH347=1)
	message("CH347 support enabled")
else()
	message("CH347 support disabled")
endif()

if (ENABLE_CMSISDAP)
	if (HIDAPI_FOUND)
		target_include_directories(openFPGALoader PRIVATE ${HIDAPI_INCLUDE_DIRS})
		target_link_directories(openFPGALoader PRIVATE ${HIDAPI_LIBRARY_DIRS})
		target_link_libraries(openFPGALoader PRIVATE ${HIDAPI_LIBRARIES})
		target_compile_definitions(openFPGALoader PRIVATE ENABLE_CMSISDAP=1)
		target_sources(openFPGALoader PRIVATE src/cmsisDAP.cpp)
		list (APPEND OPENFPGALOADER_HEADERS src/cmsisDAP.hpp)
		message("cmsis_dap support enabled")
	else()
		message("hidapi-libusb not found: cmsis_dap support disabled")
	endif()
endif(ENABLE_CMSISDAP)

# DFU
if (ENABLE_DFU)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_DFU=1)
	message("DFU support enabled")
else()
	message("DFU support disabled")
endif()

# dirtyJtag
if (ENABLE_DIRTYJTAG)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_DIRTYJTAG=1)
	message("dirtyJtag support enabled")
else()
	message("dirtyJtag support disabled")
endif()

# ESP32S3
if (ENABLE_ESP_USB)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_ESP_USB=1)
	message("ESP32S3 support enabled")
else()
	message("ESP32S3 support disabled")
endif()

# Gowin GWU2X JTAG interface
if(ENABLE_GOWIN_GWU2X)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_GOWIN_GWU2X=1)
	message("Gowin GWU2X support enabled")
else()
	message("Gowin GWU2X support disabled")
endif()

# Jetson Nano (libGPIO based)
if (ENABLE_JETSONNANOGPIO)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_JETSONNANOGPIO=1)
	message("Jetson Nano GPIO support enabled")
endif(ENABLE_JETSONNANOGPIO)

# JLINK
if (ENABLE_JLINK)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_JLINK=1)
	message("JLink support enabled")
else()
	message("JLink support disabled")
endif()

# libGPIOD support
if (ENABLE_LIBGPIOD)
	target_include_directories(openFPGALoader PRIVATE ${LIBGPIOD_INCLUDE_DIRS})
	target_link_directories(openFPGALoader PRIVATE ${LIBGPIOD_LIBRARY_DIRS})
	target_link_libraries(openFPGALoader PRIVATE ${LIBGPIOD_LIBRARIES})
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_LIBGPIOD=1)
	if (LIBGPIOD_VERSION VERSION_GREATER_EQUAL 2)
		message("libgpiod v2 support enabled")
		target_compile_definitions(openFPGALoader PRIVATE GPIOD_APIV2)
	else()
		message("libgpiod v1 support enabled")
	endif()
endif(ENABLE_LIBGPIOD)

if (ENABLE_REMOTEBITBANG)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_REMOTEBITBANG=1)
	message("Remote bitbang client support enabled")
else()
	message("Remote bitbang client support disabled")
endif()

if (ENABLE_XILINX_PLATFORM_CABLE_USB)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_XILINX_PLATFORM_CABLE_USB=1)
	message("Xilinx Platform Cable USB (XPCU) support enabled")
else()
	message("Xilinx Platform Cable USB (XPCU) support disabled")
endif()

if (ENABLE_XILINX_VIRTUAL_CABLE_CLIENT)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_XVC_CLIENT=1)
	set(CMAKE_EXE_LINKER_FLAGS "-pthread ${CMAKE_EXE_LINKER_FLAGS}")
	message("Xilinx Virtual Client support enabled")
else()
	message("Xilinx Virtual Client support disabled")
endif()

if (ENABLE_XILINX_VIRTUAL_CABLE_SERVER)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_XVC_SERVER=1)
	set(CMAKE_EXE_LINKER_FLAGS "-pthread ${CMAKE_EXE_LINKER_FLAGS}")
	message("Xilinx Virtual Server support enabled")
else()
	message("Xilinx Virtual Server support disabled")
endif()

# USB Devices Scan
if (ENABLE_USB_SCAN)
	target_compile_definitions(openFPGALoader PRIVATE ENABLE_USB_SCAN=1)
endif()

if (ZLIB_FOUND)
	target_include_directories(openFPGALoader PRIVATE ${ZLIB_INCLUDE_DIRS})
	target_link_libraries(openFPGALoader PRIVATE ${ZLIB_LIBRARIES})
	target_compile_definitions(openFPGALoader PRIVATE HAS_ZLIB=1)
else()
	message("zlib library not found: can't flash intel/altera devices")
	message("or reads compressed bitstreams")
endif()

if (LINK_CMAKE_THREADS)
	find_package(Threads REQUIRED)
	target_link_libraries(openFPGALoader PRIVATE Threads::Threads)
endif()

if (USE_LIBFTDI)
	# libftdi < 1.4 as no usb_addr
	# libftdi >= 1.5 as purge_buffer obsolete
	math(EXPR FTDI_VAL "${LIBFTDI_VERSION_MAJOR} * 100 + ${LIBFTDI_VERSION_MINOR}")
	target_compile_definitions(openFPGALoader PRIVATE FTDI_VERSION=${FTDI_VAL})
endif()

install(TARGETS openFPGALoader DESTINATION bin)

####################################################################################################
# SPIOverJtag bitstreams install
####################################################################################################

file(GLOB GZ_FILES spiOverJtag/spiOverJtag_*.*.gz)
file(GLOB BPI_GZ_FILES bpiOverJtag/bpiOverJtag_*.bit.gz)
list(APPEND GZ_FILES ${BPI_GZ_FILES})

# Compress rbf and bit files present into repository
# TODO: test compat with Windows and MacOS
list(INSERT CMAKE_MODULE_PATH 0 ${PROJECT_SOURCE_DIR}/cmake/Modules)
include(FindGZIP)

if (NOT ${CMAKE_SYSTEM_NAME} MATCHES "Windows" AND GZIP_PRG)
	set(SPIOVERJTAG_DIR "${CMAKE_CURRENT_SOURCE_DIR}/spiOverJtag")
	file(GLOB BITS_FILES RELATIVE ${SPIOVERJTAG_DIR} spiOverJtag/spiOverJtag_*.bit)
	file(GLOB RBF_FILES RELATIVE ${SPIOVERJTAG_DIR} spiOverJtag/spiOverJtag_*.rbf)

	STRING(REGEX REPLACE ".bit" ".bit.gz" BIT_GZ_FILES "${BITS_FILES}")
	STRING(REGEX REPLACE ".rbf" ".rbf.gz" RBF_GZ_FILES "${RBF_FILES}")

	FOREACH(bit ${BITS_FILES} ${RBF_FILES})
		ADD_CUSTOM_COMMAND(OUTPUT ${bit}.gz
			COMMAND ${GZIP_PRG} -9 -c ${bit} > ${CMAKE_CURRENT_BINARY_DIR}/${bit}.gz
			DEPENDS ${SPIOVERJTAG_DIR}/${bit}
			WORKING_DIRECTORY ${SPIOVERJTAG_DIR}
			COMMENT "Building ${bit}.gz")
		list(APPEND GZ_FILES ${CMAKE_CURRENT_BINARY_DIR}/${bit}.gz)
	ENDFOREACH(bit)

	ADD_CUSTOM_TARGET(bit ALL DEPENDS ${BIT_GZ_FILES} ${RBF_GZ_FILES})
else()
	file(GLOB BITS_FILES spiOverJtag/spiOverJtag_*.bit)
	file(GLOB RBF_FILES spiOverJtag/spiOverJtag_*.rbf)
	install(FILES
		${BITS_FILES}
		${RBF_FILES}
		DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/openFPGALoader
	)
endif()

install(FILES
	${GZ_FILES}
	DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/openFPGALoader
)
