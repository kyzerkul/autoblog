/**
 * Projects Management JavaScript
 * Handles UI interactions for the projects page
 */

$(document).ready(function() {
    // Initialize modals
    const createProjectModal = new bootstrap.Modal(document.getElementById('createProjectModal'));
    const projectDetailsModal = new bootstrap.Modal(document.getElementById('projectDetailsModal'));

    // Load projects on page load
    loadProjects();

    // Create project button click
    $('#createProjectBtn').on('click', function() {
        createProjectModal.show();
    });

    // Save project button click
    $('#saveProjectBtn').on('click', function() {
        saveProject();
    });

    /**
     * Load all projects from the API
     */
    function loadProjects() {
        $('#projectsLoading').removeClass('d-none');
        $('#noProjectsMessage').addClass('d-none');
        $('#projectsList').find('.project-card-container').remove();

        $.ajax({
            url: '/api/projects',
            type: 'GET',
            success: function(response) {
                $('#projectsLoading').addClass('d-none');
                
                if (response.status === 'success') {
                    if (response.projects && response.projects.length > 0) {
                        renderProjects(response.projects);
                    } else {
                        $('#noProjectsMessage').removeClass('d-none');
                    }
                } else {
                    showError('Error loading projects: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                $('#projectsLoading').addClass('d-none');
                $('#noProjectsMessage').removeClass('d-none');
                showError('Error loading projects: ' + error);
            }
        });
    }

    /**
     * Render the list of projects
     * @param {Array} projects List of projects to render
     */
    function renderProjects(projects) {
        projects.forEach(function(project) {
            const projectCard = `
                <div class="col-md-4 mb-4 project-card-container">
                    <div class="card project-card" data-project-id="${project.id}">
                        <div class="card-header bg-primary text-white">
                            ${project.name}
                            <span class="card-header-action">
                                <span class="badge bg-${project.active ? 'success' : 'secondary'} status-badge">
                                    ${project.active ? 'Active' : 'Inactive'}
                                </span>
                            </span>
                        </div>
                        <div class="card-body">
                            <p class="card-text">
                                <strong>Created:</strong> ${new Date(project.created_at).toLocaleString()}
                            </p>
                            <div class="d-grid gap-2">
                                <button class="btn btn-outline-primary btn-sm view-project-btn" data-project-id="${project.id}">
                                    <i class="bi bi-eye"></i> View Details
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            $('#projectsList').append(projectCard);
        });

        // Add event listeners to view project buttons
        $('.view-project-btn').on('click', function() {
            const projectId = $(this).data('project-id');
            viewProjectDetails(projectId);
        });
    }

    /**
     * View project details
     * @param {string} projectId The ID of the project to view
     */
    function viewProjectDetails(projectId) {
        $.ajax({
            url: `/api/projects/${projectId}`,
            type: 'GET',
            success: function(response) {
                if (response.status === 'success') {
                    renderProjectDetails(response.project);
                    projectDetailsModal.show();
                } else {
                    showError('Error loading project details: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError('Error loading project details: ' + error);
            }
        });
    }

    /**
     * Render project details in the modal
     * @param {Object} project The project details to render
     */
    function renderProjectDetails(project) {
        $('#projectDetailsTitle').text(project.name);

        let wpSiteHtml = '';
        if (project.wordpress_site) {
            wpSiteHtml = `
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">WordPress Site</div>
                    <div class="card-body">
                        <h5 class="card-title">${project.wordpress_site.name}</h5>
                        <p class="card-text">
                            <strong>URL:</strong> <a href="${project.wordpress_site.url}" target="_blank">${project.wordpress_site.url}</a><br>
                            <strong>Username:</strong> ${project.wordpress_site.username}
                        </p>
                        <button class="btn btn-sm btn-outline-info test-connection-btn" data-site-id="${project.wordpress_site.id}">
                            <i class="bi bi-check-circle"></i> Test Connection
                        </button>
                    </div>
                </div>
            `;
        }

        let channelsHtml = '<div class="card mb-3"><div class="card-header bg-success text-white">YouTube Channels</div><div class="card-body">';
        
        if (project.channels && project.channels.length > 0) {
            project.channels.forEach(function(channel) {
                const isMonitoring = channel.is_monitoring ? 'Running' : 'Stopped';
                const statusBadgeClass = channel.is_monitoring ? 'success' : 'danger';
                
                channelsHtml += `
                    <div class="channel-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>Channel ID:</strong> ${channel.channel_id}
                                <span class="badge bg-${statusBadgeClass} ms-2">${isMonitoring}</span>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-${channel.is_monitoring ? 'danger' : 'success'} toggle-monitoring-btn" 
                                        data-channel-id="${channel.id}" 
                                        data-project-id="${project.id}" 
                                        data-action="${channel.is_monitoring ? 'stop' : 'start'}">
                                    <i class="bi bi-${channel.is_monitoring ? 'stop-circle' : 'play-circle'}"></i> 
                                    ${channel.is_monitoring ? 'Stop' : 'Start'} Monitoring
                                </button>
                            </div>
                        </div>
                        <div class="mt-2">
                            <div class="form-check form-switch">
                                <input class="form-check-input toggle-auto-publish" type="checkbox" 
                                       id="autoPublish${channel.id}" ${channel.auto_publish ? 'checked' : ''}
                                       data-channel-id="${channel.id}" data-project-id="${project.id}">
                                <label class="form-check-label" for="autoPublish${channel.id}">Auto-publish to WordPress</label>
                            </div>
                        </div>
                    </div>
                `;
            });
        } else {
            channelsHtml += '<p>No channels configured for this project.</p>';
        }
        
        channelsHtml += `
                <div class="mt-3">
                    <button class="btn btn-sm btn-outline-success add-channel-btn" data-project-id="${project.id}">
                        <i class="bi bi-plus-circle"></i> Add Channel
                    </button>
                </div>
            </div>
        </div>`;

        const publishedArticlesHtml = `
            <div class="card mb-3">
                <div class="card-header bg-warning text-dark">Published Articles</div>
                <div class="card-body">
                    <button class="btn btn-sm btn-outline-warning" id="viewArticlesBtn" data-project-id="${project.id}">
                        <i class="bi bi-list-ul"></i> View Published Articles
                    </button>
                </div>
            </div>
        `;

        const projectActionsHtml = `
            <div class="card">
                <div class="card-header bg-dark text-white">Project Actions</div>
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <button class="btn btn-sm btn-outline-primary edit-project-btn" data-project-id="${project.id}">
                            <i class="bi bi-pencil"></i> Edit Project
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-project-btn" data-project-id="${project.id}">
                            <i class="bi bi-trash"></i> Delete Project
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Combine all HTML sections
        const detailsHtml = wpSiteHtml + channelsHtml + publishedArticlesHtml + projectActionsHtml;
        $('#projectDetailsContent').html(detailsHtml);

        // Add event listeners for the buttons
        addProjectDetailEventListeners(project);
    }

    /**
     * Add event listeners to buttons in the project details modal
     * @param {Object} project The project data
     */
    function addProjectDetailEventListeners(project) {
        // Test WordPress connection
        $('.test-connection-btn').on('click', function() {
            const siteId = $(this).data('site-id');
            testWordPressConnection(project.id, siteId);
        });

        // Toggle channel monitoring
        $('.toggle-monitoring-btn').on('click', function() {
            const channelId = $(this).data('channel-id');
            const projectId = $(this).data('project-id');
            const action = $(this).data('action');
            toggleChannelMonitoring(projectId, channelId, action);
        });

        // Toggle auto-publish
        $('.toggle-auto-publish').on('change', function() {
            const channelId = $(this).data('channel-id');
            const projectId = $(this).data('project-id');
            const autoPublish = $(this).prop('checked');
            toggleAutoPublish(projectId, channelId, autoPublish);
        });

        // Add channel button
        $('.add-channel-btn').on('click', function() {
            const projectId = $(this).data('project-id');
            showAddChannelForm(projectId);
        });

        // View published articles
        $('#viewArticlesBtn').on('click', function() {
            const projectId = $(this).data('project-id');
            viewPublishedArticles(projectId);
        });

        // Edit project
        $('.edit-project-btn').on('click', function() {
            const projectId = $(this).data('project-id');
            editProject(projectId);
        });

        // Delete project
        $('.delete-project-btn').on('click', function() {
            const projectId = $(this).data('project-id');
            confirmDeleteProject(projectId);
        });
    }

    /**
     * Save a new project
     */
    function saveProject() {
        // Validate form
        const projectName = $('#projectName').val();
        const wpName = $('#wpName').val();
        const wpUrl = $('#wpUrl').val();
        const wpUsername = $('#wpUsername').val();
        const wpPassword = $('#wpPassword').val();
        const youtubeRSS = $('#youtubeRSS').val();
        const autoPublish = $('#autoPublish').prop('checked');

        if (!projectName || !wpName || !wpUrl || !wpUsername || !wpPassword) {
            showError('Please fill in all required fields');
            return;
        }

        // Prepare data for API
        const projectData = {
            name: projectName,
            wp_name: wpName,
            wp_url: wpUrl,
            wp_username: wpUsername,
            wp_password: wpPassword,
            youtube_rss: youtubeRSS,
            auto_publish: autoPublish
        };

        // Send API request
        $.ajax({
            url: '/api/projects',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(projectData),
            success: function(response) {
                if (response.status === 'success') {
                    createProjectModal.hide();
                    resetCreateForm();
                    loadProjects();
                    showSuccess('Project created successfully');
                } else {
                    showError('Error creating project: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError('Error creating project: ' + error);
            }
        });
    }

    /**
     * Reset the create project form
     */
    function resetCreateForm() {
        $('#createProjectForm')[0].reset();
    }

    /**
     * Show an error message
     * @param {string} message The error message to show
     */
    function showError(message) {
        // You can implement your own error handling here
        alert(message);
    }

    /**
     * Show a success message
     * @param {string} message The success message to show
     */
    function showSuccess(message) {
        // You can implement your own success handling here
        alert(message);
    }

    // Implemented functions for project management actions
    function testWordPressConnection(projectId, siteId) {
        $.ajax({
            url: `/api/projects/${projectId}/wordpress/test`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({}), // Simplified - no need to send site_id
            success: function(response) {
                if (response.status === 'success') {
                    showSuccess('WordPress connection successful!');
                } else {
                    showError('WordPress connection test failed: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError('Error testing WordPress connection: ' + error);
            }
        });
    }

    function toggleChannelMonitoring(projectId, channelId, action) {
        const endpoint = action === 'start' ? 'start' : 'stop';
        $.ajax({
            url: `/api/projects/${projectId}/channels/${channelId}/${endpoint}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({}),
            success: function(response) {
                if (response.status === 'success') {
                    showSuccess(`Monitoring ${action === 'start' ? 'started' : 'stopped'} successfully`);
                    // Refresh the project details
                    viewProjectDetails(projectId);
                } else {
                    showError(`Error ${action}ing monitoring: ` + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError(`Error ${action}ing monitoring: ` + error);
            }
        });
    }

    function toggleAutoPublish(projectId, channelId, autoPublish) {
        $.ajax({
            url: `/api/projects/${projectId}/channels/${channelId}/autopublish`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ auto_publish: autoPublish }),
            success: function(response) {
                if (response.status === 'success') {
                    showSuccess(`Auto-publish ${autoPublish ? 'enabled' : 'disabled'} successfully`);
                } else {
                    showError('Error updating auto-publish setting: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError('Error updating auto-publish setting: ' + error);
            }
        });
    }

    function showAddChannelForm(projectId) {
        // Create a modal with a form to add a new channel
        const formHtml = `
            <div class="modal fade" id="addChannelModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Add YouTube Channel</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="addChannelForm">
                                <div class="mb-3">
                                    <label for="channelId" class="form-label">YouTube Channel ID or RSS URL</label>
                                    <input type="text" class="form-control" id="channelId" required 
                                           placeholder="UCsBjURrPoezykLs9EqgamOA or RSS URL">
                                    <div class="form-text">Enter the YouTube Channel ID or complete RSS URL</div>
                                </div>
                                <div class="form-check mb-3">
                                    <input class="form-check-input" type="checkbox" id="channelAutoPublish" checked>
                                    <label class="form-check-label" for="channelAutoPublish">
                                        Auto-publish articles to WordPress
                                    </label>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="saveChannelBtn">Add Channel</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove any existing modal
        $('#addChannelModal').remove();
        
        // Add the modal to the page
        $('body').append(formHtml);
        
        // Initialize the modal
        const addChannelModal = new bootstrap.Modal(document.getElementById('addChannelModal'));
        
        // Show the modal
        addChannelModal.show();
        
        // Add event listener for the save button
        $('#saveChannelBtn').on('click', function() {
            const channelId = $('#channelId').val();
            const autoPublish = $('#channelAutoPublish').prop('checked');
            
            if (!channelId) {
                showError('Please enter a Channel ID or RSS URL');
                return;
            }
            
            // Prepare data for API
            const data = {
                channel_id: channelId,
                auto_publish: autoPublish
            };
            
            // Add the channel to the project
            $.ajax({
                url: `/api/projects/${projectId}/channels`,
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify(data),
                success: function(response) {
                    if (response.status === 'success') {
                        addChannelModal.hide();
                        showSuccess('Channel added successfully');
                        // Refresh the project details
                        setTimeout(() => {
                            viewProjectDetails(projectId);
                        }, 1000); // Short delay to ensure database has updated
                    } else {
                        showError('Error adding channel: ' + (response.error || 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) {
                    showError('Error adding channel: ' + error);
                }
            });
        });
    }

    function viewPublishedArticles(projectId) {
        $.ajax({
            url: `/api/projects/${projectId}/articles`,
            type: 'GET',
            success: function(response) {
                if (response.status === 'success') {
                    displayPublishedArticles(response.articles, projectId);
                } else {
                    showError('Error loading published articles: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError('Error loading published articles: ' + error);
            }
        });
    }
    
    function displayPublishedArticles(articles, projectId) {
        // Create a modal to display the articles
        const articlesHtml = `
            <div class="modal fade" id="publishedArticlesModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Published Articles</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            ${articles && articles.length > 0 ? `
                                <div class="table-responsive">
                                    <table class="table table-striped">
                                        <thead>
                                            <tr>
                                                <th>Title</th>
                                                <th>Published</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${articles.map(article => `
                                                <tr>
                                                    <td>${article.title}</td>
                                                    <td>${new Date(article.published_at).toLocaleString()}</td>
                                                    <td>
                                                        <a href="${article.article_url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                                            <i class="bi bi-eye"></i> View
                                                        </a>
                                                        <a href="${article.video_url}" target="_blank" class="btn btn-sm btn-outline-danger">
                                                            <i class="bi bi-youtube"></i> YouTube
                                                        </a>
                                                    </td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : `
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle"></i> No articles published yet for this project.
                                </div>
                            `}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove any existing modal
        $('#publishedArticlesModal').remove();
        
        // Add the modal to the page
        $('body').append(articlesHtml);
        
        // Initialize the modal
        const articlesModal = new bootstrap.Modal(document.getElementById('publishedArticlesModal'));
        
        // Show the modal
        articlesModal.show();
    }

    function editProject(projectId) {
        // First get the project details
        $.ajax({
            url: `/api/projects/${projectId}`,
            type: 'GET',
            success: function(response) {
                if (response.status === 'success') {
                    showEditProjectForm(response.project);
                } else {
                    showError('Error loading project details: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError('Error loading project details: ' + error);
            }
        });
    }
    
    function showEditProjectForm(project) {
        // Create a modal with a form to edit the project
        const formHtml = `
            <div class="modal fade" id="editProjectModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit Project</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="editProjectForm">
                                <div class="mb-3">
                                    <label for="editProjectName" class="form-label">Project Name</label>
                                    <input type="text" class="form-control" id="editProjectName" 
                                           required value="${project.name}">
                                </div>
                                <div class="form-check mb-3">
                                    <input class="form-check-input" type="checkbox" id="editProjectActive" 
                                           ${project.is_active ? 'checked' : ''}>
                                    <label class="form-check-label" for="editProjectActive">
                                        Active
                                    </label>
                                </div>
                                ${project.wordpress_site ? `
                                    <h6 class="mt-4">WordPress Site</h6>
                                    <div class="mb-3">
                                        <label for="editWpName" class="form-label">Site Name</label>
                                        <input type="text" class="form-control" id="editWpName" 
                                               required value="${project.wordpress_site.name}">
                                    </div>
                                    <div class="mb-3">
                                        <label for="editWpUrl" class="form-label">Site URL</label>
                                        <input type="url" class="form-control" id="editWpUrl" 
                                               required value="${project.wordpress_site.url}">
                                    </div>
                                    <div class="mb-3">
                                        <label for="editWpUsername" class="form-label">Username</label>
                                        <input type="text" class="form-control" id="editWpUsername" 
                                               required value="${project.wordpress_site.username}">
                                    </div>
                                    <div class="mb-3">
                                        <label for="editWpPassword" class="form-label">Application Password</label>
                                        <input type="password" class="form-control" id="editWpPassword" 
                                               placeholder="Leave blank to keep current password">
                                        <div class="form-text">Only enter a new password if you want to change it</div>
                                    </div>
                                ` : ''}
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="updateProjectBtn">Update Project</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove any existing modal
        $('#editProjectModal').remove();
        
        // Add the modal to the page
        $('body').append(formHtml);
        
        // Initialize the modal
        const editProjectModal = new bootstrap.Modal(document.getElementById('editProjectModal'));
        
        // Show the modal
        editProjectModal.show();
        
        // Add event listener for the update button
        $('#updateProjectBtn').on('click', function() {
            const name = $('#editProjectName').val();
            const active = $('#editProjectActive').prop('checked');
            
            if (!name) {
                showError('Please enter a project name');
                return;
            }
            
            // Prepare the data for the API
            const data = {
                name: name,
                active: active
            };
            
            // Add WordPress site details if present
            if (project.wordpress_site) {
                data.wordpress_site = {
                    id: project.wordpress_site.id,
                    name: $('#editWpName').val(),
                    url: $('#editWpUrl').val(),
                    username: $('#editWpUsername').val()
                };
                
                // Only include password if it's been changed
                const password = $('#editWpPassword').val();
                if (password) {
                    data.wordpress_site.app_password = password;
                }
            }
            
            // Update the project
            $.ajax({
                url: `/api/projects/${project.id}`,
                type: 'PUT',
                contentType: 'application/json',
                data: JSON.stringify(data),
                success: function(response) {
                    if (response.status === 'success') {
                        editProjectModal.hide();
                        showSuccess('Project updated successfully');
                        // Refresh the project list and details
                        loadProjects();
                        viewProjectDetails(project.id);
                    } else {
                        showError('Error updating project: ' + (response.error || 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) {
                    showError('Error updating project: ' + error);
                }
            });
        });
    }

    function confirmDeleteProject(projectId) {
        if (confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
            deleteProject(projectId);
        }
    }

    function deleteProject(projectId) {
        $.ajax({
            url: `/api/projects/${projectId}`,
            type: 'DELETE',
            success: function(response) {
                if (response.status === 'success') {
                    showSuccess('Project deleted successfully');
                    // Close the project details modal
                    $('#projectDetailsModal').modal('hide');
                    // Refresh the project list
                    loadProjects();
                } else {
                    showError('Error deleting project: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                showError('Error deleting project: ' + error);
            }
        });
    }
});
