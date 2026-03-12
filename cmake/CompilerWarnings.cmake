function(tcc_setup_warnings target)
  if (NOT TCC_ENABLE_WARNINGS)
    return()
  endif()

  if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE
      -Wall
      -Wextra
      -Wpedantic
    )
  endif()
endfunction()
