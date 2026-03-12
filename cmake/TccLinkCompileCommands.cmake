function(tcc_link_compile_commands source_dir binary_dir)
  if (NOT CMAKE_EXPORT_COMPILE_COMMANDS)
    return()
  endif()

  set(link_path "${source_dir}/compile_commands.json")
  set(target_path "${binary_dir}/compile_commands.json")

  execute_process(COMMAND ${CMAKE_COMMAND} -E rm -f "${link_path}")
  execute_process(COMMAND ${CMAKE_COMMAND} -E create_symlink
    "${target_path}"
    "${link_path}"
  )
endfunction()
