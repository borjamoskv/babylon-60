
tell application "Safari"
    activate
    tell front window
        repeat with t in every tab
            try
                set u to URL of t
                if u contains "details?email=" or u contains "details" then
                    set URL of t to "https://borjamoskv.substack.com/publish/subscribers/details?email=info%40naobservatory.org"
                    delay 4.5
                    
                    # 1. Click Ellipsis
                    set jsCode to "(() => { " & ¬
                        "  let btn = document.querySelector('button[aria-label=\"Ellipsis\"]');" & ¬
                        "  if (!btn) return 'ELLIPSIS_NOT_FOUND';" & ¬
                        "  btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));" & ¬
                        "  btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));" & ¬
                        "  btn.click();" & ¬
                        "  return 'ELLIPSIS_CLICKED';" & ¬
                        "})()"
                    set clickRes to do JavaScript jsCode in t
                    if clickRes is not "ELLIPSIS_CLICKED" then
                        return "FAILED_CLICK_ELLIPSIS: " & clickRes
                    end if
                    delay 0.5
                    
                    # 2. Click Quitar de la lista
                    set jsCode2 to "(() => { " & ¬
                        "  let items = Array.from(document.querySelectorAll('[role=menuitem], [role=menuitemcheckbox], [role=option], div[data-radix-menu-content] *, div[role=menu] *'));" & ¬
                        "  let removeBtn = items.find(el => el.innerText && el.innerText.trim() === 'Quitar de la lista');" & ¬
                        "  if (!removeBtn) return 'REMOVE_OPTION_NOT_FOUND';" & ¬
                        "  removeBtn.click();" & ¬
                        "  return 'OPTION_CLICKED';" & ¬
                        "})()"
                    set optionRes to do JavaScript jsCode2 in t
                    if optionRes is not "OPTION_CLICKED" then
                        return "FAILED_OPTION: " & optionRes
                    end if
                    delay 0.5
                    
                    # 3. Confirm Modal
                    set jsCode3 to "(() => { " & ¬
                        "  let confirmBtn = Array.from(document.querySelectorAll('button')).find(el => el.innerText && (el.innerText.trim() === 'Eliminar y reembolsar' || el.innerText.trim() === 'Quitar' || el.innerText.trim() === 'Quitar de la lista'));" & ¬
                        "  if (confirmBtn) {" & ¬
                        "    confirmBtn.click();" & ¬
                        "    return 'DELETED';" & ¬
                        "  } else {" & ¬
                        "    return 'CONFIRM_NOT_FOUND';" & ¬
                        "  }" & ¬
                        "})()"
                    set confirmRes to do JavaScript jsCode3 in t
                    return confirmRes
                end if
            on error e
                # Ignore
            end try
        end repeat
    end tell
    return "TAB_NOT_FOUND"
end tell
