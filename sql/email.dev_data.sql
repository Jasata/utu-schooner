--
-- Schooner - Simple Course Management System
-- email.dev_data.sql / Development and testing data set
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-23  Initial version.
--
INSERT INTO email.template
(
    template_id,
    mimetype,
    priority,
    subject,
    body
)
VALUES
(
    'HUBREG',
    'text/plain',
    'normal',
    'Your GitHub account registration was successful!',
    'Matching collaborator invitation was found and your GitHub account {{ registration.github_account }} has been successfully registered. Your execises will be automatically retrieved from repository: {{ registration.github_repository }}.

Should you, for whatever reason, need to change your GitHub account or repository, you can always revisit https://schooner.utu.fi/register.html and issue a new registration. Just remember to make the corresponding collaborator invitation as well.

Regards,

{{ course.code }}
{{ course.email }}'
);



-- EOF
