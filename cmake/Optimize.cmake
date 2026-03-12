include(CheckIPOSupported)

function(tcc_setup_optimization target)
  if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE
      $<$<CONFIG:Release>:-O3>
      $<$<CONFIG:RelWithDebInfo>:-O3>
      $<$<CONFIG:MinSizeRel>:-Os>
      $<$<CONFIG:Debug>:-O0>
      $<$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>>:-fomit-frame-pointer>
      $<$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>>:-fno-semantic-interposition>
      $<$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>>:-funroll-loops>
    )

    if (TCC_ENABLE_STRICT_ALIASING)
      target_compile_options(${target} PRIVATE -fstrict-aliasing)
    endif()

    if (TCC_ENABLE_NATIVE)
      target_compile_options(${target} PRIVATE
        $<$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>,$<CONFIG:MinSizeRel>>:-march=native>
        $<$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>,$<CONFIG:MinSizeRel>>:-mtune=native>
      )
    endif()

    if (TCC_ENABLE_VISIBILITY_HIDDEN)
      target_compile_options(${target} PRIVATE -fvisibility=hidden)
    endif()

    if (TCC_ENABLE_FAST_MATH)
      target_compile_options(${target} PRIVATE
        -ffast-math
        -fno-finite-math-only
        -fno-math-errno
        -fno-trapping-math
      )
    endif()
  endif()

  if (TCC_ENABLE_LTO)
    check_ipo_supported(RESULT ipo_ok OUTPUT ipo_err)
    if (ipo_ok)
      set_property(TARGET ${target} PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)
    endif()
  endif()
endfunction()
