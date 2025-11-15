Newcomers List → Tap Newcomer → Newcomer Detail Page

Newcomer Detail Page:
  - Summary Card
  - Weekly Update section : Comments, attended church,
  - Rest of the fields at bottom, also update-able


  --------------------------------------------------
< Back       Newcomer Title                       ...
--------------------------------------------------

[ Summary Card ]
- Location
- Contact
- Regularity

[ Weekly Update ]
Attended church this week?
-------------------------------------------
| Add your weekly update                  |
| (textbox, auto expand)                  |
|                                         |
| [ Submit Update ]                       |
-------------------------------------------

[ All Fields updateable ]
-------------------------------------------
Name     
Contact  
Location
Outstation    
Last Comment
Powerhouse Status
Powerhouse Name         
-------------------------------------------

[ Last Comment ] [Dated]
-------------------------------------------

-------------------------------------------

## Code Changes Required

### Assessment Summary
The current UI uses a side-by-side layout (list on left, detail on right) with read-only fields displayed in a flat structure. The form for updates is at the bottom. The new design requires:
- Full-page navigation pattern (List → Detail Page)
- Header with back button and menu
- Summary Card component
- Separate Weekly Update section
- Editable fields throughout
- Reorganized layout matching the new design

### Ordered Task List

1. **Add navigation state management for page transitions**
   - Add state variables to track current view (list vs detail)
   - Create functions to show/hide list and detail views
   - Update view-card CSS classes to support full-page detail view on mobile and desktop

2. **Add back button and menu button to detail view header**
   - Add back button element to `view-card__header` in detail section
   - Add menu button (three dots) to header
   - Style buttons to match design (back arrow icon, menu icon)
   - Wire up back button click handler to navigate to list view

3. **Update detail header to show newcomer name as title**
   - Change `detailViewTitle` to display selected newcomer's name dynamically
   - Remove or update subtitle text
   - Ensure title updates when newcomer is selected

4. **Create Summary Card component structure**
   - Add new HTML section for summary card after header
   - Include Location, Contact, and Regularity fields in card layout
   - Style as elevated card with border-radius and shadow
   - Position between header and weekly update section

5. **Extract and display Regularity in Summary Card**
   - Move regularity visualization from detail-panel to summary card
   - Ensure regularity data renders correctly in new location
   - Update CSS for regularity display in card context

6. **Create Weekly Update section with attendance question**
   - Add new section titled "Weekly Update"
   - Add "Attended church this week?" question with Yes/No radio buttons
   - Position above the comment textarea
   - Style to match design pattern

7. **Implement auto-expanding textarea for weekly update**
   - Update comment textarea to auto-expand based on content
   - Add JavaScript to dynamically adjust textarea height
   - Ensure smooth expansion animation
   - Set appropriate min/max heights

8. **Restructure Weekly Update form submission**
   - Move Submit Update button to be part of Weekly Update section
   - Update form structure to group attendance + comment together
   - Ensure form submission includes both attendance and comment
   - Update button styling and positioning

9. **Create editable fields section for all newcomer data**
   - Add new section titled "All Fields updateable"
   - Convert read-only fields (Name, Contact, Location, Outstation, Last Comment, Powerhouse Status, Powerhouse Name) to editable inputs
   - Use appropriate input types (text, select, textarea)
   - Style inputs to match design system

10. **Implement field editing functionality**
    - Add edit/save buttons or inline editing for each field
    - Create update handlers for individual field changes
    - Add validation for field updates
    - Update backend calls to support partial field updates

11. **Add Last Comment section with date display**
    - Create separate section showing last comment with formatted date
    - Extract date from lastUpdatedAt field
    - Display in format: "[Last Comment] [Dated]"
    - Position after editable fields section

12. **Update detail view layout order**
    - Reorder sections: Header → Summary Card → Weekly Update → All Fields → Last Comment
    - Remove old detail-panel structure
    - Ensure proper spacing and visual hierarchy
    - Update CSS for new layout flow

13. **Update responsive behavior for full-page detail view**
    - Modify CSS to hide list view when detail is shown (mobile)
    - Ensure detail view takes full width on mobile
    - Maintain side-by-side on desktop if desired, or make full-page
    - Test navigation transitions

14. **Update JavaScript selectNewcomer function for navigation**
    - Modify selectNewcomer to show detail view and hide list view
    - Add navigation state tracking
    - Ensure back button returns to list view
    - Handle browser back button if needed

15. **Update CSS for new component hierarchy**
    - Add styles for summary-card component
    - Add styles for weekly-update section
    - Add styles for editable-fields section
    - Update existing detail-panel styles or remove if unused
    - Ensure consistent spacing and typography

16. **Remove or refactor old detail-panel structure**
    - Identify unused CSS classes from old structure
    - Remove or consolidate duplicate field displays
    - Ensure all data is displayed in new structure
    - Clean up unused JavaScript references

17. **Update form submission to handle Weekly Update separately**
    - Modify submitNewcomerUpdate to handle weekly update (attendance + comment) as distinct action
    - Ensure weekly update doesn't interfere with field edits
    - Add success/error feedback for weekly updates
    - Update UI state after successful weekly update

18. **Add visual separation between sections**
    - Add dividers or spacing between Summary Card, Weekly Update, All Fields, and Last Comment
    - Ensure clear visual hierarchy
    - Match design pattern from spec
    - Test on both light and dark themes

19. **Update field update handlers for individual field edits**
    - Create separate update functions for each editable field
    - Add debouncing for text inputs if needed
    - Show loading/saving states for individual fields
    - Handle errors per field

20. **Test and fix navigation flow**
    - Test: List → Select Newcomer → Detail Page → Back → List
    - Ensure state persists correctly
    - Test on mobile and desktop
    - Fix any navigation bugs or state issues
