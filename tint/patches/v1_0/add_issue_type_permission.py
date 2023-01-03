from tint.install import after_install

def execute():
  try:
    after_install()
  except Exception as e:
    print("Failed patch", e)