ALTER TABLE SANCTION ADD
(
  FINISHED_BY_USER_ID NUMBER
, CONSTRAINT FINISHED_BY_USER_FK FOREIGN KEY (FINISHED_BY_USER_ID) REFERENCES "USER" (USER_ID)
);
