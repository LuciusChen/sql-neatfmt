UPDATE t_sys_menu m
    JOIN (SELECT menu_id
          FROM (SELECT child.menu_id
                FROM t_sys_menu child
                         JOIN t_sys_menu parent ON parent.menu_id = child.parent_id
                WHERE parent.menu_bar = '批发'
                  AND parent.module = 'oms'
                  AND child.module = 'oms'
                  AND child.menu_bar <> '省危货平台数据上报'
                  AND child.menu_bar NOT LIKE '兆基%') tmp) x
    ON x.menu_id = m.menu_id
SET m.menu_bar = CONCAT('兆基', m.menu_bar);
