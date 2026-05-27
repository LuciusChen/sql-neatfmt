SELECT CONCAT('omsmp-', t.menu_code) code,
       t.menu_bar                    name,
       t.remarks
FROM t_sys_menu t
         INNER t_role_menu a ON a.menu_id = t.menu_id
         INNER t_sys_role b ON b.role_id = a.role_id
         INNER t_section_role c ON c.role_id = b.role_id
         INNER t_sys_section d ON d.section_id = c.section_id
         INNER t_user_section e ON e.section_id = d.section_id
         INNER t_sys_user f ON f.user_id = e.user_id
WHERE f.user_id = 1
  AND t.is_button = '1'
  AND t.menu_code LIKE '04%'
  AND t.module = 'omsmp'
  AND (b.role_id < 2 OR b.role_id > 11)
ORDER BY t.menu_code;
