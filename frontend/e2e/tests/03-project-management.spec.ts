import { test, expect } from '@playwright/test';
import { AppPage } from '../utils/test-helpers';
import { API_CONFIG, PROJECT_DATA, PERFORMANCE_THRESHOLDS } from '../fixtures/test-data';

test.describe('Project Management', () => {
  let appPage: AppPage;

  test.beforeEach(async ({ page }) => {
    appPage = new AppPage(page);
    await appPage.navigateToHome();
    await appPage.waitForAppLoad();
    await appPage.configureAPI(API_CONFIG.valid);
  });

  test('should create multiple projects', async ({ page }) => {
    const projects = [PROJECT_DATA.simple, PROJECT_DATA.complex];
    
    for (const project of projects) {
      await appPage.createNewProject(project);
      await appPage.expectProjectToBeLoaded(project.title);
      await appPage.expectNotificationToShow('success', 'Project created successfully');
    }

    // Verify projects list shows all created projects
    const projectList = page.locator('[data-testid="project-list-button"]');
    await projectList.click();

    for (const project of projects) {
      const projectItem = page.locator(`[data-testid="project-item-${project.title}"]`);
      await expect(projectItem).toBeVisible();
      await expect(projectItem).toContainText(project.title);
      await expect(projectItem).toContainText(project.description);
    }
  });

  test('should load existing projects', async ({ page }) => {
    // Create a project first
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();
    await appPage.enhanceContent(0);

    // Create another project
    await appPage.createNewProject(PROJECT_DATA.complex);
    await appPage.expectProjectToBeLoaded(PROJECT_DATA.complex.title);

    // Load the first project back
    await appPage.loadProject(PROJECT_DATA.simple.title);
    await appPage.expectProjectToBeLoaded(PROJECT_DATA.simple.title);

    // Verify the outline is still there
    const outline = page.locator('[data-testid^="outline-section-"]');
    await expect(outline).toHaveCount(3); // Simple project has 3 sections

    // Verify enhanced content is preserved
    const enhancementBadge = page.locator('[data-testid="enhanced-badge-0"]');
    await expect(enhancementBadge).toBeVisible();
  });

  test('should handle project editing', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);

    // Edit project details
    const editButton = page.locator('[data-testid="edit-project-button"]');
    await editButton.click();

    const titleInput = page.locator('[data-testid="edit-project-title"]');
    await titleInput.clear();
    await titleInput.fill('Updated Project Title');

    const descriptionInput = page.locator('[data-testid="edit-project-description"]');
    await descriptionInput.clear();
    await descriptionInput.fill('Updated project description with more details');

    const saveButton = page.locator('[data-testid="save-project-changes"]');
    await saveButton.click();

    // Verify changes are saved
    await appPage.expectProjectToBeLoaded('Updated Project Title');
    await appPage.expectNotificationToShow('success', 'Project updated successfully');

    // Verify changes persist after reload
    await page.reload();
    await appPage.waitForAppLoad();
    await appPage.expectProjectToBeLoaded('Updated Project Title');
  });

  test('should duplicate projects', async ({ page }) => {
    // Create and develop a project
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();
    await appPage.enhanceContent(0);

    // Duplicate the project
    const duplicateButton = page.locator('[data-testid="duplicate-project-button"]');
    await duplicateButton.click();

    const duplicateName = page.locator('[data-testid="duplicate-name-input"]');
    await duplicateName.fill('Duplicated Project');

    const confirmDuplicate = page.locator('[data-testid="confirm-duplicate-button"]');
    await confirmDuplicate.click();

    // Verify duplicate is created
    await appPage.expectProjectToBeLoaded('Duplicated Project');
    await appPage.expectNotificationToShow('success', 'Project duplicated successfully');

    // Verify outline is duplicated
    const outline = page.locator('[data-testid^="outline-section-"]');
    await expect(outline).toHaveCount(3);

    // Verify enhanced content is duplicated
    const enhancementBadge = page.locator('[data-testid="enhanced-badge-0"]');
    await expect(enhancementBadge).toBeVisible();

    // Verify original project still exists
    const projectList = page.locator('[data-testid="project-list-button"]');
    await projectList.click();

    const originalProject = page.locator(`[data-testid="project-item-${PROJECT_DATA.simple.title}"]`);
    await expect(originalProject).toBeVisible();

    const duplicatedProject = page.locator('[data-testid="project-item-Duplicated Project"]');
    await expect(duplicatedProject).toBeVisible();
  });

  test('should delete projects with confirmation', async ({ page }) => {
    // Create multiple projects
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.createNewProject(PROJECT_DATA.complex);

    // Delete the current project
    const deleteButton = page.locator('[data-testid="delete-project-button"]');
    await deleteButton.click();

    // Should show confirmation dialog
    const confirmDialog = page.locator('[data-testid="delete-confirmation"]');
    await expect(confirmDialog).toBeVisible();
    await expect(confirmDialog).toContainText('Are you sure you want to delete this project?');

    const confirmDelete = page.locator('[data-testid="confirm-delete-button"]');
    await confirmDelete.click();

    // Should show success notification
    await appPage.expectNotificationToShow('success', 'Project deleted successfully');

    // Should load another project or show empty state
    const emptyState = page.locator('[data-testid="no-project-loaded"]');
    const projectLoaded = page.locator('[data-testid="current-project-title"]');
    
    // Either empty state or another project should be visible
    await expect(emptyState.or(projectLoaded)).toBeVisible();

    // Verify deleted project is not in the list
    const projectList = page.locator('[data-testid="project-list-button"]');
    await projectList.click();

    const deletedProject = page.locator(`[data-testid="project-item-${PROJECT_DATA.complex.title}"]`);
    await expect(deletedProject).not.toBeVisible();
  });

  test('should handle project export', async ({ page }) => {
    // Create and develop a project
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();
    await appPage.enhanceContent(0);

    // Export project
    const exportButton = page.locator('[data-testid="export-project-button"]');
    const downloadPromise = page.waitForEvent('download');
    await exportButton.click();

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/.*\.json$/);

    // Verify export notification
    await appPage.expectNotificationToShow('success', 'Project exported successfully');
  });

  test('should handle project import', async ({ page }) => {
    // Create a project export first
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();
    
    const exportButton = page.locator('[data-testid="export-project-button"]');
    const downloadPromise = page.waitForEvent('download');
    await exportButton.click();
    const download = await downloadPromise;

    // Save the download for import test
    const exportPath = await download.path();

    // Clear current project
    await appPage.createNewProject(PROJECT_DATA.complex);

    // Import the exported project
    const importButton = page.locator('[data-testid="import-project-button"]');
    await importButton.click();

    const fileInput = page.locator('[data-testid="import-file-input"]');
    await fileInput.setInputFiles(exportPath!);

    const confirmImport = page.locator('[data-testid="confirm-import-button"]');
    await confirmImport.click();

    // Verify import success
    await appPage.expectNotificationToShow('success', 'Project imported successfully');
    await appPage.expectProjectToBeLoaded(PROJECT_DATA.simple.title);

    // Verify imported content
    const outline = page.locator('[data-testid^="outline-section-"]');
    await expect(outline).toHaveCount(3);
  });

  test('should handle invalid project import files', async ({ page }) => {
    const importButton = page.locator('[data-testid="import-project-button"]');
    await importButton.click();

    // Try to import invalid file (create a temporary text file)
    const invalidFilePath = 'test-invalid-import.txt';
    
    const fileInput = page.locator('[data-testid="import-file-input"]');
    await fileInput.setInputFiles({
      name: invalidFilePath,
      mimeType: 'text/plain',
      buffer: Buffer.from('This is not a valid project file'),
    });

    const confirmImport = page.locator('[data-testid="confirm-import-button"]');
    await confirmImport.click();

    // Should show error
    await appPage.expectNotificationToShow('error', 'Invalid project file format');

    // Dialog should remain open for retry
    const importDialog = page.locator('[data-testid="import-dialog"]');
    await expect(importDialog).toBeVisible();
  });

  test('should show project statistics', async ({ page }) => {
    // Create a project with content
    await appPage.createNewProject(PROJECT_DATA.complex);
    await appPage.generateOutline();
    await appPage.enhanceContent(0);
    await appPage.enhanceContent(1);
    await appPage.searchImages('technology');
    await appPage.selectImages(3);

    // View project statistics
    const statsButton = page.locator('[data-testid="project-stats-button"]');
    await statsButton.click();

    const statsDialog = page.locator('[data-testid="project-stats-dialog"]');
    await expect(statsDialog).toBeVisible();

    // Verify statistics are displayed
    const totalSections = page.locator('[data-testid="stat-total-sections"]');
    await expect(totalSections).toContainText('5'); // Complex project has 5 sections

    const enhancedSections = page.locator('[data-testid="stat-enhanced-sections"]');
    await expect(enhancedSections).toContainText('2');

    const totalImages = page.locator('[data-testid="stat-total-images"]');
    await expect(totalImages).toContainText('3');

    const completionPercentage = page.locator('[data-testid="stat-completion"]');
    const completion = await completionPercentage.textContent();
    expect(parseInt(completion!)).toBeGreaterThan(0);
  });

  test('should handle project templates', async ({ page }) => {
    // Access template gallery
    const templatesButton = page.locator('[data-testid="templates-button"]');
    await templatesButton.click();

    const templateGallery = page.locator('[data-testid="template-gallery"]');
    await expect(templateGallery).toBeVisible();

    // Select a template
    const businessTemplate = page.locator('[data-testid="template-business"]');
    await businessTemplate.click();

    const useTemplateButton = page.locator('[data-testid="use-template-button"]');
    await useTemplateButton.click();

    // Fill template details
    const templateProjectTitle = page.locator('[data-testid="template-project-title"]');
    await templateProjectTitle.fill('Business Presentation from Template');

    const createFromTemplate = page.locator('[data-testid="create-from-template-button"]');
    await createFromTemplate.click();

    // Verify template project is created
    await appPage.expectProjectToBeLoaded('Business Presentation from Template');

    // Verify template-specific outline is generated
    const outline = page.locator('[data-testid^="outline-section-"]');
    await expect(outline.count()).toBeGreaterThan(0);

    // Verify template metadata is preserved
    const templateInfo = page.locator('[data-testid="template-info"]');
    await expect(templateInfo).toContainText('business');
  });

  test('should search and filter projects', async ({ page }) => {
    // Create multiple projects
    const projects = [
      { ...PROJECT_DATA.simple, title: 'AI Technology Presentation' },
      { ...PROJECT_DATA.complex, title: 'Business Strategy Overview' },
      { title: 'Marketing Campaign Analysis', description: 'Marketing analysis', topic: 'Marketing' },
    ];

    for (const project of projects) {
      await appPage.createNewProject(project);
    }

    // Open project list
    const projectList = page.locator('[data-testid="project-list-button"]');
    await projectList.click();

    // Search for projects
    const searchInput = page.locator('[data-testid="project-search"]');
    await searchInput.fill('Technology');

    // Should filter to show only matching projects
    const filteredResults = page.locator('[data-testid^="project-item-"]');
    await expect(filteredResults).toHaveCount(1);
    await expect(filteredResults.first()).toContainText('AI Technology Presentation');

    // Clear search
    await searchInput.clear();
    await expect(filteredResults).toHaveCount(3);

    // Test topic filter
    const topicFilter = page.locator('[data-testid="topic-filter"]');
    await topicFilter.selectOption('Marketing');

    const marketingResults = page.locator('[data-testid^="project-item-"]');
    await expect(marketingResults).toHaveCount(1);
    await expect(marketingResults.first()).toContainText('Marketing Campaign Analysis');
  });

  test('should meet performance requirements for project operations', async ({ page }) => {
    // Measure project creation time
    const createTime = await appPage.measureAPIResponseTime(async () => {
      await appPage.createNewProject(PROJECT_DATA.simple);
    });
    expect(createTime).toBeLessThan(PERFORMANCE_THRESHOLDS.navigationTime);

    // Measure project loading time
    await appPage.createNewProject(PROJECT_DATA.complex);
    
    const loadTime = await appPage.measureAPIResponseTime(async () => {
      await appPage.loadProject(PROJECT_DATA.simple.title);
    });
    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.navigationTime);

    // Measure project list loading time
    const listTime = await appPage.measureAPIResponseTime(async () => {
      const projectList = page.locator('[data-testid="project-list-button"]');
      await projectList.click();
      await page.waitForSelector('[data-testid^="project-item-"]');
    });
    expect(listTime).toBeLessThan(PERFORMANCE_THRESHOLDS.navigationTime);
  });
});