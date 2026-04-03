local system = require 'pandoc.system'

-- Helper to check if file exists
local function file_exists(name)
   local f = io.open(name, "r")
   if f ~= nil then io.close(f) return true else return false end
end

-- Create a hash of the content to use as filename
local function get_hash(content)
  return pandoc.sha1(content)
end

-- Define cache directory from environment variable if available
local cache_dir = os.getenv('SMIDIR_CACHE_DIR')
local img_dir

if cache_dir then
  img_dir = cache_dir
  -- Ensure cache directory exists, do NOT remove it
  os.execute('mkdir -p ' .. img_dir)
else
  -- Fallback to temporary directory for this run
  -- os.tmpname() returns a path to a file, so we remove it and create a directory
  img_dir = os.tmpname()
  os.execute('rm -f ' .. img_dir .. ' && mkdir -p ' .. img_dir)
end

function CodeBlock(block)
  if block.classes:includes('mermaid') then
    local content = block.text
    local hash = get_hash(content)
    local format = block.attributes['format'] or 'svg'
    local extension = '.' .. format
    local filename = img_dir .. '/' .. hash .. extension
    
    -- Check if file already exists
    if not file_exists(filename) then
      local png_width = block.attributes['png_width'] or '800'
      
      -- We'll use a temporary file for the mermaid code
      local mmd_file = os.tmpname()
      local f = io.open(mmd_file, 'w')
      f:write(content)
      f:close()
      
      local success = false
      
      if format == 'svg' then
        -- Current method: mmd -> PDF -> SVG
        local pdf_file = os.tmpname() .. '.pdf'
        
        -- Step 1: Generate PDF using mmdc
        local mmdc_cmd = string.format('npx -p @mermaid-js/mermaid-cli mmdc -i %s -o %s --pdfFit', mmd_file, pdf_file)
        print('Generating mermaid PDF for SVG output: ' .. pdf_file)
        local mmdc_success = os.execute(mmdc_cmd)
        
        if mmdc_success then
          -- Step 2: Convert PDF to SVG for better compatibility
          local pdf2svg_cmd = string.format('pdf2svg %s %s', pdf_file, filename)
          print('Converting PDF to SVG: ' .. filename)
          success = os.execute(pdf2svg_cmd)
          os.remove(pdf_file)
        else
          os.remove(pdf_file)
        end
      else
        -- Default: Generate PNG directly using mmdc
        local mmdc_cmd = string.format('npx -p @mermaid-js/mermaid-cli mmdc -i %s -o %s -w %s', mmd_file, filename, png_width)
        print('Generating mermaid PNG: ' .. filename .. ' (png_width: ' .. png_width .. ')')
        success = os.execute(mmdc_cmd)
      end
      
      -- Cleanup temporary file
      os.remove(mmd_file)
      
      if not success then
        io.stderr:write("Error: Failed to generate mermaid " .. format .. " for " .. filename .. "\n")
        return block -- Fallback to code block on error
      end
    end
    
    -- Set default width for the image if not specified
    if not block.attributes['width'] then
      block.attributes['width'] = '50%'
    end
    
    -- Return an image para
    return pandoc.Para({
      pandoc.Image({pandoc.Str(content)}, filename, "", block.attr)
    })
  end
end
