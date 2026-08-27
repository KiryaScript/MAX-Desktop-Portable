; MAX Desktop - Custom NSIS Installer Script
; Создаёт ярлык на рабочем столе с правильным описанием и иконкой

!macro customInstall
  ; Создать ярлык на рабочем столе
  CreateShortcut "$DESKTOP\MAX Desktop.lnk" "$INSTDIR\MAX-Desktop-Portable.exe" "" "$INSTDIR\MAX-Desktop-Portable.exe" 0 SW_SHOWNORMAL "" "MAX Desktop — быстрый клиент без слежки"
  
  ; Создать ярлык в меню Пуск
  CreateDirectory "$SMPROGRAMS\MAX Desktop"
  CreateShortcut "$SMPROGRAMS\MAX Desktop\MAX Desktop.lnk" "$INSTDIR\MAX-Desktop-Portable.exe" "" "$INSTDIR\MAX-Desktop-Portable.exe" 0 SW_SHOWNORMAL "" "MAX Desktop — быстрый клиент без слежки"
  CreateShortcut "$SMPROGRAMS\MAX Desktop\Удалить MAX Desktop.lnk" "$INSTDIR\Uninstall MAX Desktop.exe"
!macroend

!macro customUninstall
  ; Удалить ярлык с рабочего стола
  Delete "$DESKTOP\MAX Desktop.lnk"
  
  ; Удалить ярлыки из меню Пуск
  Delete "$SMPROGRAMS\MAX Desktop\MAX Desktop.lnk"
  Delete "$SMPROGRAMS\MAX Desktop\Удалить MAX Desktop.lnk"
  RMDir "$SMPROGRAMS\MAX Desktop"
!macroend
