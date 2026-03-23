function(hscopt_setup_warnings target)
  if (NOT HSCOPT_ENABLE_WARNINGS)
    return()
  endif()

  if (CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE
      -Wall
      -Wextra
      -Wpedantic
    )
  endif()
endfunction()
