SELECT *
FROM `bhmc-2021`.auth_user au 

UPDATE `bhmc-2021`.auth_user 
SET password = 'pbkdf2_sha256$216000$ehPFYtEsHtRM$DuP0OtP/0eW/hcDWEga/SYgdUidrHnYnGVBTVeVDldI='
WHERE id > 1

UPDATE `bhmc-2021`.register_player 
SET profile_picture_id = NULL
   ,stripe_customer_id = NULL
WHERE profile_picture_id  IS NOT NULL 
OR stripe_customer_id  IS NOT NULL 
