SELECT *
FROM `bhmc`.auth_user au 

UPDATE `bhmc`.auth_user 
SET password = 'pbkdf2_sha256$216000$ehPFYtEsHtRM$DuP0OtP/0eW/hcDWEga/SYgdUidrHnYnGVBTVeVDldI='
WHERE id > 1

UPDATE `bhmc`.register_player 
SET profile_picture_id = NULL
   ,stripe_customer_id = NULL
WHERE profile_picture_id  IS NOT NULL 
OR stripe_customer_id  IS NOT NULL 
