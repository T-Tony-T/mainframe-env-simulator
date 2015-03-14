# Table of Content #


# Bindable Functions #

## Split Window Manipulation: ##

### window-split-horz ###
| Emacs | `'C-x 3'` |
|:------|:----------|
| Vi    | `''` (_N/A_) |
| Other | `''` |

Split the current focused screen horizontally into two screen.

### window-split-vert ###
| Emacs | `'C-x 2'` |
|:------|:----------|
| Vi    | `''` |
| Other | `''` |

Split the current focused screen vertically into two screen.

### window-delete ###
| Emacs | `'C-x 0'` |
|:------|:----------|
| Vi    | `''` |
| Other | `''` |

Remove the current focused screen (the buffer shown in the screen will be un-touched).

### window-delete-other ###
| Emacs | `'C-x 1'` |
|:------|:----------|
| Vi    | `''` |
| Other | `''` |

Remove all screens but the current focused one (the buffer shown in those screens will be un-touched).


---


## Buffer Manipulation: ##

### buffer-open ###
| Emacs | `'C-x C-f'` |
|:------|:------------|
| Vi    | `''` |
| Other | `'C-o'` |

Switch the current focused screen to the browser to open a new file (buffer).

### buffer-save ###
| Emacs | `'C-x C-s'` |
|:------|:------------|
| Vi    | `''` |
| Other | `'C-s'` |

Save the buffer shown in the current focused screen.

### buffer-save-as ###
| Emacs | `'C-x C-w'` |
|:------|:------------|
| Vi    | `''` |
| Other | `'C-S'` |

Save the buffer shown in the current focused screen as another (possibly the same) file.

### buffer-close ###
| Emacs | `'C-x k'` |
|:------|:----------|
| Vi    | `''` |
| Other | `'F4'` |

Close the buffer shown in the current focused screen. This will also cause all screens which have the same buffer shown to switch to other buffers.

### buffer-undo ###
| Emacs | `'C-x u'` |
|:------|:----------|
| Vi    | `''` |
| Other | `'C-z'` |

Undo the last change mado to the buffer in the current focused screen. This will also cause all screens which have the same buffer to revert.

### buffer-redo ###
| Emacs | `''` |
|:------|:-----|
| Vi    | `''` |
| Other | `'C-y'` |

Redo the last [buffer-undo](GuiKeyBinding#buffer-undo.md) made to the buffer in the current focused screen, if applied. This will also cause all screens which have the same buffer to change.


---


## Tab Manipulation: ##

### tabbar-mode ###
| Emacs | `'F7'` |
|:------|:-------|
| Vi    | `''` |
| Other | `'F7'` |

Switch between "on", "grouped", and "off" mode. In "grouped" mode, only tabs within the same group of the current shown buffer are shown.

### tabbar-prev ###
| Emacs | `'C-Left'` |
|:------|:-----------|
| Vi    | `''` |
| Other | `'C-Left'` |

Switch the current focused screen to show the content of the previous tab's buffer. This will turn on tabbar automatically, if not already.

### tabbar-next ###
| Emacs | `'C-Right'` |
|:------|:------------|
| Vi    | `''` |
| Other | `'C-Right'` |

Switch the current focused screen to show the content of the next tab's buffer. This will turn on tabbar automatically, if not already.


---


## Editor Related Functions: ##

### align-line ###
| Emacs | `''` |
|:------|:-----|
| Vi    | `''` |
| Other | `''` |

Align the current line according to the Major Editing Mode.

### align-region ###
| Emacs | `'C-M-\'` |
|:------|:----------|
| Vi    | `''` |
| Other | `''` |

Align all lines within the selected region. This is equivalent to perform [align-line](GuiKeyBinding#align-line.md) on each line within the region successively.

### align-or-complete ###
| Emacs | `'Tab'` |
|:------|:--------|
| Vi    | `''` |
| Other | `'Tab'` |

If at word-end, complete the current typing; otherwise, align the current line.

### complete ###
| Emacs | `''` |
|:------|:-----|
| Vi    | `''` |
| Other | `''` |

Try complete the current typing as much as possible, based on the current completion mode.

### complete-list ###
| Emacs | `'M-/'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Show a list of all possible completions of the current typing; Notice that two successive fail in [complete](GuiKeyBinding#complete.md) will also cause the list to show.

### backward-char ###
| Emacs | `'C-b'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the previous character.

### backward-delete-char ###
| Emacs | `'BackSpace'` |
|:------|:--------------|
| Vi    | `''` |
| Other | `'BackSpace'` |

Delete the previous character.

### forward-char ###
| Emacs | `'C-f'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the next character.

### forward-delete-char ###
| Emacs | `'Delete'` |
|:------|:-----------|
| Vi    | `''` |
| Other | `'Delete'` |

Delete the next character.

### backward-word ###
| Emacs | `'M-b'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the start of the current word, or the previous word if not currently inside one.

### backward-delete-word ###
| Emacs | `'M-D'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Kill to the start of the current word, or kill the previous word if not currently inside one. This will put the killed word(s) into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### forward-word ###
| Emacs | `'M-f'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the end of the current word, or the next word if not currently inside one.

### forward-delete-word ###
| Emacs | `'M-d'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Kill to the end of the current word, or kill the next word if not currently inside one. This will put the killed word(s) into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### backward-line ###
| Emacs | `'C-a'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the start of the current line.

### backward-delete-line ###
| Emacs | `'C-K'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Kill to the start of the current line. This will put the killed line(s) into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### forward-line ###
| Emacs | `'C-e'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the end of the current line.

### forward-delete-line ###
| Emacs | `'C-k'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Kill to the end of the current line, or kill the entire current line if at line start, or kill the new-line character if at line end. This will put the killed line(s) into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### backward-para ###
| Emacs | `'M-{'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the start of the current paragraph, or the previous paragraph if not currently inside one or at the start of a paragraph.

### backward-delete-para ###
| Emacs | `'M-K'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Kill to the start of the current paragraph, or kill the previous paragraph if not currently inside one or at the start of a paragraph. This will put the killed paragraph(s) into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### forward-para ###
| Emacs | `'M-}'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Move the cursor to the end of the current paragraph, or the next paragraph if not currently inside one or at the end of a paragraph.

### forward-delete-para ###
| Emacs | `'M-k'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Kill to the end of the current paragraph, or kill the next paragraph if not currently inside one or at the end of a paragraph. This will put the killed paragraph(s) into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### kill-region ###
| Emacs | `'C-w'` |
|:------|:--------|
| Vi    | `''` |
| Other | `'C-x'` |

Kill, otherwise known as "cut", the selected region. This will put the killed region into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### kill-ring-save ###
| Emacs | `'M-w'` |
|:------|:--------|
| Vi    | `''` |
| Other | `'C-c'` |

Save, otherwise known as "copy", the selected region into the kill-ring and unset the selection mark. This will put the saved region into the kill-ring, which can then be yanked back. (see [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) and [kill-ring-yank-pop](GuiKeyBinding#kill-ring-yank-pop.md) for more details.)

### kill-ring-yank ###
| Emacs | `'C-y'` |
|:------|:--------|
| Vi    | `''` |
| Other | `'C-v'` |

Restore the last text (region) being yanked (if any) or being killed. This is otherwise known as "paste".

### kill-ring-yank-pop ###
| Emacs | `'M-y'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Replace the just-yanked text (region) with the one before it; **require** [kill-ring-yank](GuiKeyBinding#kill-ring-yank.md) as an immidiate precedent command.

### set-mark-command ###
| Emacs | `'C-@'` |
|:------|:--------|
| Vi    | `''` |
| Other | `''` |

Set the selection mark at the current cursor position.

### set-mark-move-left ###
| Emacs | `'S-Left'` |
|:------|:-----------|
| Vi    | `''` |
| Other | `'S-Left'` |

Set the selection mark on the initial invoke, move the cursor 1 character left on each initialized invoke.

### set-mark-move-right ###
| Emacs | `'S-Right'` |
|:------|:------------|
| Vi    | `''` |
| Other | `'S-Right'` |

Set the selection mark on the initial invoke, move the cursor 1 character right on each initialized invoke.

### set-mark-move-up ###
| Emacs | `'S-Up'` |
|:------|:---------|
| Vi    | `''` |
| Other | `'S-Up'` |

Set the selection mark on the initial invoke, move the cursor 1 line up (if not first line) on each initialized invoke.

### set-mark-move-down ###
| Emacs | `'S-Down'` |
|:------|:-----------|
| Vi    | `''` |
| Other | `'S-Down'` |

Set the selection mark on the initial invoke, move the cursor 1 line down (if not last line) on each initialized invoke.

### set-mark-move-start ###
| Emacs | `'S-Home'` |
|:------|:-----------|
| Vi    | `''` |
| Other | `'S-Home'` |

Set the selection mark on the initial invoke, move the cursor to the start of the buffer on each initialized invoke.

### set-mark-move-end ###
| Emacs | `'S-End'` |
|:------|:----------|
| Vi    | `''` |
| Other | `'S-End'` |

Set the selection mark on the initial invoke, move the cursor to the end of the buffer on each initialized invoke.

### set-mark-select-all ###
| Emacs | `'C-x h'` |
|:------|:----------|
| Vi    | `''` |
| Other | `'C-a'` |

Set the selection mark at the end of the buffer and move the cursor to the start of the buffer, selecting the entire content of the buffer.


---


## Top-Level Functions ##

### prog-show-config ###
| Emacs | `'C-c c'` |
|:------|:----------|
| Vi    | `''` |
| Other | `'C-p'` |

Show the Config Console.

### prog-show-error ###
| Emacs | `'C-c e'` |
|:------|:----------|
| Vi    | `''` |
| Other | `'C-J'` |

Show the Error Console.

### prog-show-about ###
| Emacs | `''` |
|:------|:-----|
| Vi    | `''` |
| Other | `''` |

Show the About dialog.

### prog-quit ###
| Emacs | `'C-x C-c'` |
|:------|:------------|
| Vi    | `''` |
| Other | `'C-q'` |

Quit the program. Any modified buffer except **`*scratch*`** will be prompt for saving (in the so called "last-line").


---


## zPE (simulator) Related Functions: ##

### zPE-submit ###
| Emacs | `'F9'` |
|:------|:-------|
| Vi    | `''` |
| Other | `'F9'` |

Submit the file corresponding to the buffer shown in the current focused screen. **Any unsaved change will not take effects**. Notice that `*scratch*` cannot be submitted unless [saved](GuiKeyBinding#buffer-save-as.md) first.

### zPE-submit-with-JCL ###
| Emacs | `'F8'` |
|:------|:-------|
| Vi    | `''` |
| Other | `'F8'` |

Submit the file corresponding to the buffer shown in the current focused screen, with default JCL wrapped around. This should only be used to quick-test a program. Nothice that [test-run](GuiKeyBinding#zPE-submit-with-JCL.md) `*scratch*` will cause the (unsaved) buffer content to be submitted with default JCL.