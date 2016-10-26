/* Add new flags to WORKFLOW_ITEM table */
alter table
    WORKFLOW_ITEM
add (IS_WORKFLOW number(1, 0) DEFAULT 0 NOT NULL,
     IS_BUILDING_AUTHORITY number(1, 0) DEFAULT 0 NOT NULL);

/* Add new field GROUP to WORKFLOW_ENTRY */
alter table
    WORKFLOW_ENTRY
add
    "GROUP" number NOT NULL
add constraint instance_groups unique (
        INSTANCE_ID,
        WORKFLOW_ITEM_ID,
        "GROUP"
    );

/* Create new table BUILDING_AUTHORITY_SECTION */
CREATE TABLE BUILDING_AUTHORITY_SECTION (
    BUILDING_AUTHORITY_SECTION_ID NUMBER NOT NULL,
    NAME VARCHAR2(128) NOT NULL,
    CONSTRAINT BUILDING_AUTHORITY_SECTION_PK PRIMARY KEY (
        BUILDING_AUTHORITY_ID
    )
    ENABLE
);

/* Create new table BUILDING_AUTHORITY_COMMENT */
CREATE TABLE BUILDING_AUTHORITY_COMMENT (
  BUILDING_AUTHORITY_COMMENT_ID NUMBER NOT NULL,
  BUILDING_AUTHORITY_SECTION_ID NUMBER NOT NULL,
  TEXT VARCHAR2(4000 BYTE),
  "GROUP" NUMBER NOT NULL,
  CONSTRAINT BUILDING_AUTHORITY_COMMENT_PK PRIMARY KEY (
    BUILDING_AUTHORITY_COMMENT_ID
  ) ENABLE
);

ALTER TABLE BUILDING_AUTHORITY_COMMENT
ADD CONSTRAINT BUILDING_AUTHORITY_COMMEN_UK1 UNIQUE (
  BUILDING_AUTHORITY_SECTION_ID,
  "GROUP"
) ENABLE;

ALTER TABLE BUILDING_AUTHORITY_COMMENT
ADD CONSTRAINT BUILDING_AUTHORITY_COMMEN_FK1 FOREIGN KEY (
  BUILDING_AUTHORITY_SECTION_ID
)
REFERENCES BUILDING_AUTHORITY_SECTION (
  BUILDING_AUTHORITY_SECTION_ID
) ENABLE;

/* Create BUILDING_AUTHORITY_SECTION_DIS table (DIS stands for disabled) */
CREATE TABLE BUILDING_AUTHORITY_SECTION_DIS (
  BA_SECTION_DIS_ID NUMBER NOT NULL,
  INSTANCE_ID NUMBER NOT NULL,
  CONSTRAINT BA_SECTION_DIS_PK PRIMARY KEY (
    BA_SECTION_DIS_ID
  )
  USING INDEX (
      CREATE UNIQUE INDEX BUILDING_AUTHORITY_SECTION_PK1 ON BUILDING_AUTHORITY_SECTION_DIS (BA_SECTION_DIS_ID ASC) 
  ) ENABLE
);

ALTER TABLE BUILDING_AUTHORITY_SECTION_DIS
ADD CONSTRAINT BA_SECTION_DIS_FK1 FOREIGN KEY (
  INSTANCE_ID
)
REFERENCES INSTANCE (
  INSTANCE_ID
) ENABLE;

/* Create BUILDING_AUTHORITY_ITEM_DIS table (DIS stands for disabled) */
CREATE TABLE BUILDING_AUTHORITY_ITEM_DIS (
  BA_ITEM_DIS_ID NUMBER NOT NULL,
  WORKFLOW_ITEM_ID NUMBER NOT NULL,
  INSTANCE_ID NUMBER NOT NULL,
  CONSTRAINT BA_ITEM_DIS_PK PRIMARY KEY (
    BA_ITEM_DIS_ID
  )
  USING INDEX (
      CREATE UNIQUE INDEX BUILDING_AUTHORITY_ITEM_DI_PK ON BUILDING_AUTHORITY_ITEM_DIS (BA_ITEM_DIS_ID ASC)
  ) ENABLE
);

ALTER TABLE BUILDING_AUTHORITY_ITEM_DIS
ADD CONSTRAINT BA_ITEM_DIS_FK1 FOREIGN KEY (
  WORKFLOW_ITEM_ID
)
REFERENCES WORKFLOW_ITEM (
  WORKFLOW_ITEM_ID
) ENABLE;

ALTER TABLE BUILDING_AUTHORITY_ITEM_DIS
ADD CONSTRAINT BA_ITEM_DIS_FK2 FOREIGN KEY (
  INSTANCE_ID
)
REFERENCES INSTANCE (
  INSTANCE_ID
) ENABLE;

/* Create BUILDING_AUTHORITY_BUTTON table */
CREATE TABLE BUILDING_AUTHORITY_BUTTON (
  BUILDING_AUTHORITY_BUTTON_ID NUMBER NOT NULL,
  LABEL VARCHAR2(128 CHAR) NOT NULL,
  CONSTRAINT BUILDING_AUTHORITY_BUTTON_PK PRIMARY KEY (
    BUILDING_AUTHORITY_BUTTON_ID
  ) ENABLE
);

/* Create BUILDING_AUTHORITY_BUTTON_STATE table */
CREATE TABLE BUILDING_AUTHORITY_BUTTONSTATE (
  BA_BUTTON_STATE_ID NUMBER NOT NULL,
  BUILDING_AUTHORITY_BUTTON_ID NUMBER NOT NULL,
  INSTANCE_ID NUMBER NOT NULL,
  IS_CLICKED NUMBER(1) DEFAULT 0 NOT NULL,
  IS_DISABLED NUMBER(1) DEFAULT 0 NOT NULL,
  CONSTRAINT BA_BUTTONSTATE_PK PRIMARY KEY (
    BA_BUTTON_STATE_ID
  )
  USING INDEX (
    CREATE UNIQUE INDEX BUILDING_AUTHORITY_BUTTONS_PK ON BUILDING_AUTHORITY_BUTTONSTATE (BA_BUTTON_STATE_ID ASC) 
  ) ENABLE
);

ALTER TABLE BUILDING_AUTHORITY_BUTTONSTATE
ADD CONSTRAINT BA_BUTTONSTATE_FK1 FOREIGN KEY (
  BUILDING_AUTHORITY_BUTTON_ID
)
REFERENCES BUILDING_AUTHORITY_BUTTON (
  BUILDING_AUTHORITY_BUTTON_ID
) ENABLE;

ALTER TABLE BUILDING_AUTHORITY_BUTTONSTATE
ADD CONSTRAINT BA_BUTTONSTATE_FK2 FOREIGN KEY (
  INSTANCE_ID
)
REFERENCES INSTANCE (
  INSTANCE_ID
) ENABLE;

/* Create BUILDING_AUTHORITY_EMAIL table */
CREATE TABLE BUILDING_AUTHORITY_EMAIL (
  BUILDING_AUTHORITY_EMAIL_ID NUMBER NOT NULL,
  BUILDING_AUTHORITY_BUTTON_ID NUMBER NOT NULL,
  EMAIL_TEXT VARCHAR2(4000 BYTE),
  RECEIVER_QUERY VARCHAR2(4000 BYTE),
  CONSTRAINT BUILDING_AUTHORITY_EMAIL_PK PRIMARY KEY (
    BUILDING_AUTHORITY_EMAIL_ID
  ) ENABLE
);

ALTER TABLE BUILDING_AUTHORITY_EMAIL
ADD CONSTRAINT BUILDING_AUTHORITY_EMAIL_FK1 FOREIGN KEY (
  BUILDING_AUTHORITY_BUTTON_ID
)
REFERENCES BUILDING_AUTHORITY_BUTTON (
  BUILDING_AUTHORITY_BUTTON_ID
) ENABLE;

/* Create BUILDING_AUTHORITY_DOC table */
CREATE TABLE BUILDING_AUTHORITY_DOC (
  BUILDING_AUTHORITY_DOC_ID NUMBER NOT NULL,
  BUILDING_AUTHORITY_BUTTON_ID NUMBER NOT NULL,
  TEMPLATE_CLASS_ID NUMBER NOT NULL,
  TEMPLATE_ID NUMBER NOT NULL,
  CONSTRAINT BUILDING_AUTHORITY_DOC_PK PRIMARY KEY (
    BUILDING_AUTHORITY_DOC_ID
  ) ENABLE
);

ALTER TABLE BUILDING_AUTHORITY_DOC
ADD CONSTRAINT BUILDING_AUTHORITY_DOC_FK1 FOREIGN KEY (
  BUILDING_AUTHORITY_BUTTON_ID
)
REFERENCES BUILDING_AUTHORITY_BUTTON (
  BUILDING_AUTHORITY_BUTTON_ID
) ENABLE;

ALTER TABLE BUILDING_AUTHORITY_DOC
ADD CONSTRAINT BUILDING_AUTHORITY_DOC_FK2 FOREIGN KEY (
  TEMPLATE_CLASS_ID
)
REFERENCES DOCGEN_TEMPLATE_CLASS (
  DOCGEN_TEMPLATE_CLASS_ID
) ENABLE;

ALTER TABLE BUILDING_AUTHORITY_DOC
ADD CONSTRAINT BUILDING_AUTHORITY_DOC_FK3 FOREIGN KEY (
  TEMPLATE_ID
)
REFERENCES DOCGEN_TEMPLATE (
  DOCGEN_TEMPLATE_ID
) ENABLE;
