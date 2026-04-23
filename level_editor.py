import bpy

bl_info = {
    "name": "LevelEditor",
    "author": "Taro Kamata",
    "version": (1, 0),
    "blender": (3, 3, 1),
    "location": "",
    "description": "LevelEditor",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}

def register():
    print("The level editor has been enabled.")
    
def unregister():
    print("The level editor has been disabled.")

if __name__ == "__main__":
    register()