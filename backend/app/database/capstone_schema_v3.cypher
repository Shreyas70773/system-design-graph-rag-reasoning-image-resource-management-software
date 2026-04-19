CREATE CONSTRAINT capstone_scene_id IF NOT EXISTS
FOR (s:CapstoneScene) REQUIRE s.scene_id IS UNIQUE;

CREATE CONSTRAINT capstone_user_id IF NOT EXISTS
FOR (u:CapstoneUser) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT capstone_object_id IF NOT EXISTS
FOR (o:CapstoneImageObject) REQUIRE o.object_id IS UNIQUE;

CREATE CONSTRAINT capstone_text_id IF NOT EXISTS
FOR (t:CapstoneTextRegion) REQUIRE t.text_id IS UNIQUE;

CREATE CONSTRAINT capstone_edit_id IF NOT EXISTS
FOR (e:CapstoneEditEvent) REQUIRE e.event_id IS UNIQUE;

CREATE CONSTRAINT capstone_version_id IF NOT EXISTS
FOR (v:CapstoneCanvasVersion) REQUIRE v.version_id IS UNIQUE;
